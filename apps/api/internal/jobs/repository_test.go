package jobs

import (
	"bytes"
	"context"
	"log"
	"strings"
	"testing"
	"time"

	"content-creator-agent/internal/db"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

func testJobsDB(t *testing.T) *gorm.DB {
	t.Helper()
	gdb, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	require.NoError(t, err)
	require.NoError(t, gdb.Exec(`CREATE TABLE jobs (
		id TEXT PRIMARY KEY,
		chat_id TEXT NOT NULL,
		user_id TEXT NOT NULL,
		status TEXT NOT NULL,
            post_format TEXT NOT NULL DEFAULT 'legacy_html',
            generation_mode TEXT,
            expected_version_id TEXT,
            target_schema_version INTEGER,
		error_msg TEXT,
		stage TEXT NOT NULL DEFAULT 'queued',
		progress INTEGER NOT NULL DEFAULT 0,
		heartbeat_at DATETIME,
		error_code TEXT,
		created_at DATETIME,
		updated_at DATETIME
	)`).Error)
	return gdb
}

func TestJobRepository_CreateAndGet(t *testing.T) {
	gdb := testJobsDB(t)
	ctx := context.Background()
	id := uuid.New()
	chatID := uuid.New()
	userID := uuid.New()
	now := time.Now().UTC()
	j := &db.Job{
		ID:        id,
		ChatID:    chatID,
		UserID:    userID,
		Status:    db.JobStatusPending,
		CreatedAt: now,
		UpdatedAt: now,
	}
	require.NoError(t, gdb.WithContext(ctx).Create(j).Error)

	var got db.Job
	require.NoError(t, gdb.WithContext(ctx).First(&got, "id = ?", id).Error)
	require.Equal(t, id, got.ID)
	require.Equal(t, chatID, got.ChatID)
	require.Equal(t, userID, got.UserID)
	require.Equal(t, db.JobStatusPending, got.Status)
}

func TestJobRepository_UpdateStatus(t *testing.T) {
	gdb := testJobsDB(t)
	repo := NewRepository(gdb)
	ctx := context.Background()
	id := uuid.New()
	now := time.Now().UTC()
	j := &db.Job{
		ID:        id,
		ChatID:    uuid.New(),
		UserID:    uuid.New(),
		Status:    db.JobStatusPending,
		CreatedAt: now,
		UpdatedAt: now,
	}
	require.NoError(t, gdb.WithContext(ctx).Create(j).Error)

	msg := "worker failed"
	require.NoError(t, repo.UpdateStatus(ctx, id, db.JobStatusFailed, &msg))

	var got db.Job
	require.NoError(t, gdb.WithContext(ctx).First(&got, "id = ?", id).Error)
	require.Equal(t, db.JobStatusFailed, got.Status)
	require.NotNil(t, got.ErrorMsg)
	require.Equal(t, msg, *got.ErrorMsg)

	require.NoError(t, repo.UpdateStatus(ctx, id, db.JobStatusDone, nil))
	var got2 db.Job
	require.NoError(t, gdb.WithContext(ctx).First(&got2, "id = ?", id).Error)
	require.Equal(t, db.JobStatusDone, got2.Status)
}

func TestJobRepository_FailStuckProcessingJobs(t *testing.T) {
	gdb := testJobsDB(t)
	repo := NewRepository(gdb)
	ctx := context.Background()
	old := time.Now().UTC().Add(-2 * time.Hour)
	recent := time.Now().UTC().Add(-5 * time.Minute)

	stuckID := uuid.New()
	freshID := uuid.New()
	require.NoError(t, gdb.Create(&db.Job{
		ID:        stuckID,
		ChatID:    uuid.New(),
		UserID:    uuid.New(),
		Status:    db.JobStatusProcessing,
		CreatedAt: old,
		UpdatedAt: old,
	}).Error)
	require.NoError(t, gdb.Create(&db.Job{
		ID:        freshID,
		ChatID:    uuid.New(),
		UserID:    uuid.New(),
		Status:    db.JobStatusProcessing,
		CreatedAt: recent,
		UpdatedAt: recent,
	}).Error)

	cutoff := time.Now().UTC().Add(-1 * time.Hour)
	n, err := repo.FailStuckProcessingJobs(ctx, cutoff, StuckJobErrorMsg)
	require.NoError(t, err)
	require.Equal(t, int64(1), n)

	var stuck, fresh db.Job
	require.NoError(t, gdb.First(&stuck, "id = ?", stuckID).Error)
	require.Equal(t, db.JobStatusFailed, stuck.Status)
	require.NotNil(t, stuck.ErrorMsg)
	require.Equal(t, StuckJobErrorMsg, *stuck.ErrorMsg)
	require.Equal(t, "failed", stuck.Stage)
	require.Equal(t, 100, stuck.Progress)
	require.NotNil(t, stuck.ErrorCode)
	require.Equal(t, "stuck_processing", *stuck.ErrorCode)

	require.NoError(t, gdb.First(&fresh, "id = ?", freshID).Error)
	require.Equal(t, db.JobStatusProcessing, fresh.Status)
}

func TestJobRepository_UpdateProgress(t *testing.T) {
	gdb := testJobsDB(t)
	repo := NewRepository(gdb)
	ctx := context.Background()
	id := uuid.New()
	now := time.Now().UTC()
	require.NoError(t, gdb.WithContext(ctx).Create(&db.Job{
		ID:        id,
		ChatID:    uuid.New(),
		UserID:    uuid.New(),
		Status:    db.JobStatusProcessing,
		Stage:     "dispatching",
		Progress:  0,
		CreatedAt: now,
		UpdatedAt: now,
	}).Error)

	code := "temporary"
	require.NoError(t, repo.UpdateProgress(ctx, id, "rendering_slides", 88, &code))

	var got db.Job
	require.NoError(t, gdb.WithContext(ctx).First(&got, "id = ?", id).Error)
	require.Equal(t, "rendering_slides", got.Stage)
	require.Equal(t, 88, got.Progress)
	require.NotNil(t, got.HeartbeatAt)
	require.NotNil(t, got.ErrorCode)
	require.Equal(t, code, *got.ErrorCode)

	require.NoError(t, repo.UpdateProgress(ctx, id, "generating_slides", 55, nil))
	var retry db.Job
	require.NoError(t, gdb.WithContext(ctx).First(&retry, "id = ?", id).Error)
	require.Equal(t, "generating_slides", retry.Stage)
	require.Equal(t, 88, retry.Progress)
}

func TestFailIfActivePreservesTerminalJobs(t *testing.T) {
	original := log.Writer()
	var output bytes.Buffer
	log.SetOutput(&output)
	t.Cleanup(func() { log.SetOutput(original) })
	gdb := testJobsDB(t)
	repo := NewRepository(gdb)
	ctx := context.Background()
	for _, status := range []db.JobStatus{db.JobStatusProcessing, db.JobStatusDone, db.JobStatusFailed} {
		id := uuid.New()
		require.NoError(t, gdb.Create(&db.Job{ID: id, ChatID: uuid.New(), UserID: uuid.New(), Status: status}).Error)
		changed, err := repo.FailIfActive(ctx, id, "dispatch rejected")
		require.NoError(t, err)
		require.Equal(t, status == db.JobStatusProcessing, changed)
		var got db.Job
		require.NoError(t, gdb.First(&got, "id = ?", id).Error)
		if status == db.JobStatusProcessing {
			require.Equal(t, db.JobStatusFailed, got.Status)
		} else {
			require.Equal(t, status, got.Status)
		}
	}
	require.Equal(t, 1, strings.Count(output.String(), "event=job_terminal"))
	require.Contains(t, output.String(), "code=DISPATCH_FAILED")
}

func TestWatchdogEmitsTerminalEventsOncePerFormat(t *testing.T) {
	gdb := testJobsDB(t)
	repo := NewRepository(gdb)
	old := time.Now().UTC().Add(-2 * time.Hour)
	for _, format := range []db.PostFormat{db.PostFormatLegacy, db.PostFormatStructuredV1} {
		require.NoError(t, gdb.Create(&db.Job{ID: uuid.New(), ChatID: uuid.New(), UserID: uuid.New(), Status: db.JobStatusProcessing, PostFormat: format, CreatedAt: old, UpdatedAt: old}).Error)
	}
	original := log.Writer()
	var output bytes.Buffer
	log.SetOutput(&output)
	t.Cleanup(func() { log.SetOutput(original) })
	cutoff := time.Now().UTC().Add(-time.Hour)
	n, err := repo.FailStuckProcessingJobs(context.Background(), cutoff, StuckJobErrorMsg)
	require.NoError(t, err)
	require.EqualValues(t, 2, n)
	n, err = repo.FailStuckProcessingJobs(context.Background(), cutoff, StuckJobErrorMsg)
	require.NoError(t, err)
	require.Zero(t, n)
	require.Equal(t, 2, strings.Count(output.String(), "event=job_terminal"))
	require.Contains(t, output.String(), "format=legacy_html")
	require.Contains(t, output.String(), "format=structured_v1")
	require.Contains(t, output.String(), "code=STUCK_PROCESSING")
	require.Contains(t, output.String(), "duration_ms=")
}
