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
	repo := NewRepository(gdb)
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

	got, err := repo.GetByID(ctx, id)
	require.NoError(t, err)
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

	got, err := repo.GetByID(ctx, id)
	require.NoError(t, err)
	require.Equal(t, db.JobStatusFailed, got.Status)
	require.NotNil(t, got.ErrorMsg)
	require.Equal(t, msg, *got.ErrorMsg)

	require.NoError(t, repo.UpdateStatus(ctx, id, db.JobStatusDone, nil))
	got2, err := repo.GetByID(ctx, id)
	require.NoError(t, err)
	require.Equal(t, db.JobStatusDone, got2.Status)
}
