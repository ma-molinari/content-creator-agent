//go:build integration

package integration

import (
	"context"
	"errors"
	"fmt"
	"testing"
	"time"

	"content-creator-agent/internal/chat"
	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

type failingCleanupStore struct{ mockStorage }

func (failingCleanupStore) DeleteMany(context.Context, []string) error {
	return errors.New("unavailable")
}

func TestEvictionPersistsCleanupInventoryBeforeCascade(t *testing.T) {
	env := newTestEnv(t, nil)
	userID := uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: userID, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", userID) })
	ids := make([]uuid.UUID, 5)
	for i := range ids {
		ids[i] = uuid.New()
		require.NoError(t, env.DB.Create(&db.Chat{ID: ids[i], UserID: userID, PostType: db.PostTypeSingle, CreatedAt: time.Now().Add(time.Duration(i) * time.Minute)}).Error)
	}
	old, jobID, contentID := ids[0], uuid.New(), uuid.New()
	require.NoError(t, env.DB.Create(&db.Job{ID: jobID, ChatID: old, UserID: userID, Status: db.JobStatusDone}).Error)
	require.NoError(t, env.DB.Create(&db.ChatContent{ID: contentID, ChatID: old, Role: db.ChatContentRoleAssistant, Content: "ok"}).Error)
	key := fmt.Sprintf("slides/%s/slide_01.jpeg", jobID)
	html := fmt.Sprintf("slides/%s/slide_01.html", jobID)
	require.NoError(t, env.DB.Create(&db.ChatContentImage{ID: uuid.New(), ChatContentID: contentID, S3Key: key, HtmlS3Key: &html, URL: "url", SlideNumber: 1}).Error)
	svc := chat.NewService(chat.NewRepository(env.DB), jobs.NewRepository(env.DB), failingCleanupStore{}, nil, nil, nil)
	_, err := svc.CreateChat(context.Background(), userID, "single")
	require.NoError(t, err)
	var record struct {
		ObjectKeys string
		JobIDs     string
	}
	require.NoError(t, env.DB.Table("chat_cleanup_tasks").Where("chat_id = ?", old).Take(&record).Error)
	t.Cleanup(func() { env.DB.Exec("DELETE FROM chat_cleanup_tasks WHERE chat_id = ?", old) })
	require.Contains(t, record.ObjectKeys, key)
	require.Contains(t, record.ObjectKeys, html)
	require.Contains(t, record.JobIDs, jobID.String())
	var count int64
	require.NoError(t, env.DB.Model(&db.Chat{}).Where("id = ?", old).Count(&count).Error)
	require.Zero(t, count)
}
