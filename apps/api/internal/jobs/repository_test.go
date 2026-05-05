package jobs

import (
	"context"
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
		error_msg TEXT,
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

	require.NoError(t, gdb.First(&fresh, "id = ?", freshID).Error)
	require.Equal(t, db.JobStatusProcessing, fresh.Status)
}
