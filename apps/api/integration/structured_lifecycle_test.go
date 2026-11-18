//go:build integration

package integration

import (
	"context"
	"fmt"
	"testing"

	"content-creator-agent/internal/chat"
	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"content-creator-agent/internal/profile"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

// The worker and S3 are simulated; PostgreSQL performs the real transactions and locks.
func TestStructuredCreateEditAndOutOfOrderCallbacks(t *testing.T) {
	env := newTestEnv(t, nil)
	ctx := context.Background()
	uid := uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: uid, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", uid) })
	profiles := profile.NewRepository(env.DB)
	require.NoError(t, profiles.Upsert(ctx, uid, "audit", "brand"))
	worker := &captureStructuredWorker{}
	svc := chat.NewService(chat.NewRepository(env.DB), jobs.NewRepository(env.DB), mockStorage{}, profiles, nil, worker)
	svc.ConfigureStructured(true, func(context.Context) bool { return true })
	ch, err := svc.CreateChatWithClient(ctx, uid, "single", true)
	require.NoError(t, err)
	create, err := svc.PostMessageWithOptions(ctx, uid, ch.ID, "crie", nil, chat.MessageOptions{Mode: "create", ClientSupported: true})
	require.NoError(t, err)
	require.Equal(t, create.JobID, worker.payload.JobID)
	complete := func(jobID uuid.UUID) (bool, bool, error) {
		prefix := fmt.Sprintf("slides/%s/", jobID)
		html := prefix + "slide_01.html"
		return jobs.CompleteStructuredReply(ctx, env.DB, jobID, "ok", []jobs.ArtifactRef{{S3Key: prefix + "slide_01.jpeg", HtmlS3Key: &html, SlideNumber: 1}}, jobs.StructuredArtifact{DocumentS3Key: prefix + "document.json", SchemaVersion: 1, RendererVersion: "1"}, mockStorage{})
	}
	done, conflict, err := complete(create.JobID)
	require.NoError(t, err)
	require.False(t, done)
	require.False(t, conflict)
	var first db.PostVersion
	require.NoError(t, env.DB.Where("job_id = ?", create.JobID).First(&first).Error)
	opts := chat.MessageOptions{Mode: "edit", BaseVersionID: first.ID.String(), ClientSupported: true}
	oldEdit, err := svc.PostMessageWithOptions(ctx, uid, ch.ID, "primeira edição", nil, opts)
	require.NoError(t, err)
	newEdit, err := svc.PostMessageWithOptions(ctx, uid, ch.ID, "segunda edição", nil, opts)
	require.NoError(t, err)
	require.Equal(t, first.ID, *worker.payload.BaseVersionID)
	require.Equal(t, first.DocumentS3Key, worker.payload.DocumentS3Key)
	done, conflict, err = complete(newEdit.JobID)
	require.NoError(t, err)
	require.False(t, done)
	require.False(t, conflict)
	done, conflict, err = complete(oldEdit.JobID)
	require.NoError(t, err)
	require.False(t, done)
	require.True(t, conflict)
	done, conflict, err = complete(newEdit.JobID)
	require.NoError(t, err)
	require.True(t, done)
	require.False(t, conflict)
	var versions []db.PostVersion
	require.NoError(t, env.DB.Where("chat_id = ?", ch.ID).Find(&versions).Error)
	require.Len(t, versions, 2)
	var latest db.PostVersion
	require.NoError(t, env.DB.Where("job_id = ?", newEdit.JobID).First(&latest).Error)
	require.NotNil(t, latest.ParentVersionID)
	require.Equal(t, first.ID, *latest.ParentVersionID)
	require.NotEqual(t, first.DocumentS3Key, latest.DocumentS3Key)
	var persisted db.Chat
	require.NoError(t, env.DB.First(&persisted, "id = ?", ch.ID).Error)
	require.Equal(t, latest.ID, *persisted.CurrentVersionID)
	_, err = svc.PostMessageWithOptions(ctx, uid, ch.ID, "edição obsoleta", nil, opts)
	require.ErrorIs(t, err, chat.ErrVersionConflict)
	var failed db.Job
	require.NoError(t, env.DB.First(&failed, "id = ?", oldEdit.JobID).Error)
	require.Equal(t, db.JobStatusFailed, failed.Status)
	require.Equal(t, "VERSION_CONFLICT", *failed.ErrorCode)
}
