//go:build integration

package integration

import (
	"context"
	"errors"
	"fmt"
	"testing"

	"content-creator-agent/internal/chat"
	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"content-creator-agent/internal/profile"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

type dispatchFunc func(context.Context, jobs.DispatchPayload) error

func (f dispatchFunc) DispatchJob(ctx context.Context, p jobs.DispatchPayload) error {
	return f(ctx, p)
}

func TestDispatchFailureCannotOverwriteCommittedCallback(t *testing.T) {
	env := newTestEnv(t, nil)
	ctx := context.Background()
	uid := uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: uid, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", uid) })
	profiles := profile.NewRepository(env.DB)
	require.NoError(t, profiles.Upsert(ctx, uid, "audit", "brand"))
	worker := dispatchFunc(func(ctx context.Context, p jobs.DispatchPayload) error {
		prefix := fmt.Sprintf("slides/%s/", p.JobID)
		html := prefix + "slide_01.html"
		_, _, err := jobs.CompleteStructuredReply(ctx, env.DB, p.JobID, "ok", []jobs.ArtifactRef{{S3Key: prefix + "slide_01.jpeg", HtmlS3Key: &html, SlideNumber: 1}}, jobs.StructuredArtifact{DocumentS3Key: prefix + "document.json", SchemaVersion: 1, RendererVersion: "1"}, mockStorage{})
		require.NoError(t, err)
		return errors.New("worker dispatch rejected")
	})
	svc := chat.NewService(chat.NewRepository(env.DB), jobs.NewRepository(env.DB), mockStorage{}, profiles, nil, worker)
	svc.ConfigureStructured(true, func(context.Context) bool { return true })
	ch, err := svc.CreateChatWithClient(ctx, uid, "single", true)
	require.NoError(t, err)
	result, err := svc.PostMessageWithOptions(ctx, uid, ch.ID, "crie", nil, chat.MessageOptions{Mode: "create", ClientSupported: true})
	require.NoError(t, err)
	require.NotNil(t, result)
	var job db.Job
	require.NoError(t, env.DB.First(&job, "id = ?", result.JobID).Error)
	require.Equal(t, db.JobStatusDone, job.Status)
	var count int64
	require.NoError(t, env.DB.Model(&db.PostVersion{}).Where("job_id = ?", job.ID).Count(&count).Error)
	require.EqualValues(t, 1, count)
}

func TestUnknownDispatchLeavesJobForCallbackOrWatchdog(t *testing.T) {
	env := newTestEnv(t, nil)
	ctx := context.Background()
	uid := uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: uid, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", uid) })
	profiles := profile.NewRepository(env.DB)
	require.NoError(t, profiles.Upsert(ctx, uid, "audit", "brand"))
	worker := dispatchFunc(func(context.Context, jobs.DispatchPayload) error { return jobs.ErrDispatchOutcomeUnknown })
	svc := chat.NewService(chat.NewRepository(env.DB), jobs.NewRepository(env.DB), mockStorage{}, profiles, nil, worker)
	svc.ConfigureStructured(true, func(context.Context) bool { return true })
	ch, err := svc.CreateChatWithClient(ctx, uid, "single", true)
	require.NoError(t, err)
	result, err := svc.PostMessageWithOptions(ctx, uid, ch.ID, "crie", nil, chat.MessageOptions{Mode: "create", ClientSupported: true})
	require.NoError(t, err)
	var job db.Job
	require.NoError(t, env.DB.First(&job, "id = ?", result.JobID).Error)
	require.Equal(t, db.JobStatusProcessing, job.Status)
}
