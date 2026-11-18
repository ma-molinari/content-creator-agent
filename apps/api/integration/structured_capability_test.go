//go:build integration

package integration

import (
	"context"
	"testing"

	"content-creator-agent/internal/chat"
	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"content-creator-agent/internal/profile"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

type captureStructuredWorker struct{ payload jobs.DispatchPayload }

func (w *captureStructuredWorker) DispatchJob(_ context.Context, payload jobs.DispatchPayload) error {
	w.payload = payload
	return nil
}

func TestStructuredCreationNegotiationAndRollback(t *testing.T) {
	env := newTestEnv(t, nil)
	uid := uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: uid, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", uid) })
	profiles := profile.NewRepository(env.DB)
	require.NoError(t, profiles.Upsert(context.Background(), uid, "audit", "brand"))
	worker := &captureStructuredWorker{}
	svc := chat.NewService(chat.NewRepository(env.DB), jobs.NewRepository(env.DB), mockStorage{}, profiles, nil, worker)
	ctx := context.Background()
	svc.ConfigureStructured(true, func(context.Context) bool { return false })
	_, err := svc.CreateChatWithClient(ctx, uid, "single", true)
	require.ErrorIs(t, err, chat.ErrStructuredUnavailable)
	var count int64
	require.NoError(t, env.DB.Model(&db.Chat{}).Where("user_id = ?", uid).Count(&count).Error)
	require.Zero(t, count)
	legacy, err := svc.CreateChatWithClient(ctx, uid, "single", false)
	require.NoError(t, err)
	require.Equal(t, db.PostFormatLegacy, legacy.PostFormat)
	svc.ConfigureStructured(true, func(context.Context) bool { return true })
	structured, err := svc.CreateChatWithClient(ctx, uid, "single", true)
	require.NoError(t, err)
	require.Equal(t, db.PostFormatStructuredV1, structured.PostFormat)
	_, err = svc.PostMessageWithOptions(ctx, uid, structured.ID, "crie", nil, chat.MessageOptions{Mode: "create", ClientSupported: false})
	require.ErrorIs(t, err, chat.ErrClientUpgrade)
	// Disabling new structured chats must not disable editing/creation inside existing structured chats.
	svc.ConfigureStructured(false, func(context.Context) bool { return true })
	_, err = svc.PostMessageWithOptions(ctx, uid, structured.ID, "crie", nil, chat.MessageOptions{Mode: "create", ClientSupported: true})
	require.NoError(t, err)
	require.Equal(t, "structured_v1", worker.payload.PostFormat)
	require.Equal(t, "create", worker.payload.GenerationMode)
	require.Nil(t, worker.payload.BaseVersionID)
}
