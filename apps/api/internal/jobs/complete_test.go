package jobs

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"testing"
	"time"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/storage"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

type testStore struct{}

func (testStore) Upload(context.Context, string, []byte) error { return nil }

func (testStore) GetSignedURL(context.Context, string, time.Duration) (string, error) {
	return "https://example.com/signed", nil
}

func (testStore) HeadObject(context.Context, string) error { return nil }

func (testStore) GetObject(context.Context, string) ([]byte, error) { return nil, nil }

func (testStore) Delete(context.Context, string) error { return nil }

func (testStore) DeleteMany(context.Context, []string) error { return nil }

func testCompleteSchemaDB(t *testing.T) *gorm.DB {
	t.Helper()
	gdb, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	require.NoError(t, err)
	stmts := []string{
		`CREATE TABLE chats (
			id TEXT PRIMARY KEY,
			user_id TEXT NOT NULL,
			post_type TEXT NOT NULL,
			title TEXT,
			created_at DATETIME,
			updated_at DATETIME
		)`,
		`CREATE TABLE chat_content (
			id TEXT PRIMARY KEY,
			chat_id TEXT NOT NULL,
			role TEXT NOT NULL,
			content TEXT NOT NULL,
			created_at DATETIME,
			updated_at DATETIME,
			FOREIGN KEY (chat_id) REFERENCES chats(id)
		)`,
		`CREATE TABLE chat_content_image (
			id TEXT PRIMARY KEY,
			chat_content_id TEXT NOT NULL,
			s3_key TEXT NOT NULL,
			url TEXT NOT NULL,
			slide_number INTEGER NOT NULL,
			html_s3_key TEXT,
			created_at DATETIME,
			updated_at DATETIME,
			FOREIGN KEY (chat_content_id) REFERENCES chat_content(id)
		)`,
		`CREATE TABLE jobs (
			id TEXT PRIMARY KEY,
			chat_id TEXT NOT NULL,
			user_id TEXT NOT NULL,
			status TEXT NOT NULL,
			error_msg TEXT,
			stage TEXT NOT NULL DEFAULT 'queued',
			progress INTEGER NOT NULL DEFAULT 0,
			heartbeat_at DATETIME,
			error_code TEXT,
			worker_metadata TEXT,
			created_at DATETIME,
			updated_at DATETIME
		)`,
	}
	for _, q := range stmts {
		require.NoError(t, gdb.Exec(q).Error)
	}
	return gdb
}

func TestCompleteAssistantReply_persistsWorkerMetadata(t *testing.T) {
	ctx := context.Background()
	gdb := testCompleteSchemaDB(t)
	jobID := uuid.New()
	chatID := uuid.New()
	userID := uuid.New()
	now := time.Now().UTC()
	require.NoError(t, gdb.Create(&db.Chat{
		ID:        chatID,
		UserID:    userID,
		PostType:  db.PostTypeSingle,
		CreatedAt: now,
		UpdatedAt: now,
	}).Error)
	require.NoError(t, gdb.Create(&db.Job{
		ID:        jobID,
		ChatID:    chatID,
		UserID:    userID,
		Status:    db.JobStatusProcessing,
		CreatedAt: now,
		UpdatedAt: now,
	}).Error)

	key := "slides/" + jobID.String() + "/slide_01.jpeg"
	raw := json.RawMessage(`{"pipelineVersion":"worker-v2-json-html","retryCount":1}`)
	done, err := CompleteAssistantReply(
		ctx,
		gdb,
		jobID,
		"reply",
		[]ArtifactRef{{S3Key: key, SlideNumber: 1}},
		testStore{},
		&raw,
	)
	require.NoError(t, err)
	require.False(t, done)

	var job db.Job
	require.NoError(t, gdb.First(&job, "id = ?", jobID).Error)
	require.NotNil(t, job.WorkerMetadata)
	require.Contains(t, *job.WorkerMetadata, "worker-v2-json-html")
}

func TestCompleteAssistantReply_idempotentWhenAlreadyDone(t *testing.T) {
	gdb := testCompleteSchemaDB(t)
	ctx := context.Background()
	jobID := uuid.New()
	chatID := uuid.New()
	now := time.Now().UTC()
	require.NoError(t, gdb.Create(&db.Job{
		ID:        jobID,
		ChatID:    chatID,
		UserID:    uuid.New(),
		Status:    db.JobStatusDone,
		CreatedAt: now,
		UpdatedAt: now,
	}).Error)

	done, err := CompleteAssistantReply(ctx, gdb, jobID, "hello", nil, testStore{})
	require.NoError(t, err)
	require.True(t, done)

	var n int64
	require.NoError(t, gdb.Model(&db.ChatContent{}).Count(&n).Error)
	require.Zero(t, n)
}

func TestCompleteAssistantReply_conflictWhenFailed(t *testing.T) {
	gdb := testCompleteSchemaDB(t)
	ctx := context.Background()
	jobID := uuid.New()
	chatID := uuid.New()
	now := time.Now().UTC()
	msg := "prior failure"
	require.NoError(t, gdb.Create(&db.Job{
		ID:        jobID,
		ChatID:    chatID,
		UserID:    uuid.New(),
		Status:    db.JobStatusFailed,
		ErrorMsg:  &msg,
		CreatedAt: now,
		UpdatedAt: now,
	}).Error)

	_, err := CompleteAssistantReply(ctx, gdb, jobID, "hello", nil, testStore{})
	require.ErrorIs(t, err, ErrJobCompleteConflict)
}

func TestCompleteAssistantReply_successThenIdempotent(t *testing.T) {
	gdb := testCompleteSchemaDB(t)
	ctx := context.Background()
	jobID := uuid.New()
	chatID := uuid.New()
	userID := uuid.New()
	now := time.Now().UTC()
	require.NoError(t, gdb.Create(&db.Chat{
		ID:        chatID,
		UserID:    userID,
		PostType:  db.PostTypeSingle,
		CreatedAt: now,
		UpdatedAt: now,
	}).Error)
	require.NoError(t, gdb.Create(&db.Job{
		ID:        jobID,
		ChatID:    chatID,
		UserID:    userID,
		Status:    db.JobStatusProcessing,
		CreatedAt: now,
		UpdatedAt: now,
	}).Error)

	key := "slides/" + jobID.String() + "/slide-1.jpg"
	artifacts := []ArtifactRef{{S3Key: key, SlideNumber: 1}}

	done, err := CompleteAssistantReply(ctx, gdb, jobID, "first reply", artifacts, testStore{})
	require.NoError(t, err)
	require.False(t, done)

	done2, err := CompleteAssistantReply(ctx, gdb, jobID, "retry", artifacts, testStore{})
	require.NoError(t, err)
	require.True(t, done2)

	var contents int64
	require.NoError(t, gdb.Model(&db.ChatContent{}).Where("chat_id = ?", chatID).Count(&contents).Error)
	require.Equal(t, int64(1), contents)

	var j db.Job
	require.NoError(t, gdb.First(&j, "id = ?", jobID).Error)
	require.Equal(t, db.JobStatusDone, j.Status)
}

func TestCompleteAssistantReply_persistsHtmlS3KeyWhenPresent(t *testing.T) {
	gdb := testCompleteSchemaDB(t)
	ctx := context.Background()
	jobID := uuid.New()
	chatID := uuid.New()
	userID := uuid.New()
	now := time.Now().UTC()
	require.NoError(t, gdb.Create(&db.Chat{
		ID:        chatID,
		UserID:    userID,
		PostType:  db.PostTypeSingle,
		CreatedAt: now,
		UpdatedAt: now,
	}).Error)
	require.NoError(t, gdb.Create(&db.Job{
		ID:        jobID,
		ChatID:    chatID,
		UserID:    userID,
		Status:    db.JobStatusProcessing,
		CreatedAt: now,
		UpdatedAt: now,
	}).Error)

	jpegKey := "slides/" + jobID.String() + "/slide_01.jpeg"
	htmlKey := "slides/" + jobID.String() + "/slide_01.html"
	artifacts := []ArtifactRef{{
		S3Key:       jpegKey,
		SlideNumber: 1,
		HtmlS3Key:   &htmlKey,
	}}

	_, err := CompleteAssistantReply(ctx, gdb, jobID, "reply with html", artifacts, testStore{})
	require.NoError(t, err)

	var img db.ChatContentImage
	require.NoError(t, gdb.First(&img, "s3_key = ?", jpegKey).Error)
	require.NotNil(t, img.HtmlS3Key)
	require.Equal(t, htmlKey, *img.HtmlS3Key)
}

func TestApplyWorkerFailure_noopWhenDone(t *testing.T) {
	gdb := testCompleteSchemaDB(t)
	ctx := context.Background()
	jobID := uuid.New()
	now := time.Now().UTC()
	require.NoError(t, gdb.Create(&db.Job{
		ID:        jobID,
		ChatID:    uuid.New(),
		UserID:    uuid.New(),
		Status:    db.JobStatusDone,
		CreatedAt: now,
		UpdatedAt: now,
	}).Error)

	noop, err := ApplyWorkerFailure(ctx, gdb, jobID, "late error")
	require.NoError(t, err)
	require.True(t, noop)
}

func TestApplyWorkerFailure_marksProcessingFailed(t *testing.T) {
	gdb := testCompleteSchemaDB(t)
	ctx := context.Background()
	jobID := uuid.New()
	now := time.Now().UTC()
	require.NoError(t, gdb.Create(&db.Job{
		ID:        jobID,
		ChatID:    uuid.New(),
		UserID:    uuid.New(),
		Status:    db.JobStatusProcessing,
		CreatedAt: now,
		UpdatedAt: now,
	}).Error)

	noop, err := ApplyWorkerFailure(ctx, gdb, jobID, "worker oops")
	require.NoError(t, err)
	require.False(t, noop)

	var j db.Job
	require.NoError(t, gdb.First(&j, "id = ?", jobID).Error)
	require.Equal(t, db.JobStatusFailed, j.Status)
	require.NotNil(t, j.ErrorMsg)
	require.Equal(t, "worker oops", *j.ErrorMsg)
}

func TestCompleteAssistantReply_notFound(t *testing.T) {
	gdb := testCompleteSchemaDB(t)
	ctx := context.Background()
	_, err := CompleteAssistantReply(ctx, gdb, uuid.New(), "x", nil, testStore{})
	require.ErrorIs(t, err, gorm.ErrRecordNotFound)
}

func TestCompleteAssistantReply_pendingNotAllowed(t *testing.T) {
	gdb := testCompleteSchemaDB(t)
	ctx := context.Background()
	jobID := uuid.New()
	now := time.Now().UTC()
	require.NoError(t, gdb.Create(&db.Job{
		ID:        jobID,
		ChatID:    uuid.New(),
		UserID:    uuid.New(),
		Status:    db.JobStatusPending,
		CreatedAt: now,
		UpdatedAt: now,
	}).Error)

	_, err := CompleteAssistantReply(ctx, gdb, jobID, "x", nil, testStore{})
	require.True(t, errors.Is(err, ErrJobNotProcessing))
}

type headMissingStore struct{ testStore }

func (headMissingStore) HeadObject(context.Context, string) error {
	return fmt.Errorf("wrap: %w", storage.ErrObjectNotFound)
}

func TestCompleteAssistantReply_rejectsMissingS3Object(t *testing.T) {
	gdb := testCompleteSchemaDB(t)
	ctx := context.Background()
	jobID := uuid.New()
	chatID := uuid.New()
	userID := uuid.New()
	now := time.Now().UTC()
	require.NoError(t, gdb.Create(&db.Chat{
		ID:        chatID,
		UserID:    userID,
		PostType:  db.PostTypeSingle,
		CreatedAt: now,
		UpdatedAt: now,
	}).Error)
	require.NoError(t, gdb.Create(&db.Job{
		ID:        jobID,
		ChatID:    chatID,
		UserID:    userID,
		Status:    db.JobStatusProcessing,
		CreatedAt: now,
		UpdatedAt: now,
	}).Error)

	key := "slides/" + jobID.String() + "/slide-1.jpg"
	_, err := CompleteAssistantReply(ctx, gdb, jobID, "hello", []ArtifactRef{{S3Key: key, SlideNumber: 1}}, headMissingStore{})
	require.ErrorIs(t, err, ErrArtifactObjectNotFound)

	var contents int64
	require.NoError(t, gdb.Model(&db.ChatContent{}).Where("chat_id = ?", chatID).Count(&contents).Error)
	require.Zero(t, contents)

	var j db.Job
	require.NoError(t, gdb.First(&j, "id = ?", jobID).Error)
	require.Equal(t, db.JobStatusProcessing, j.Status)
}
