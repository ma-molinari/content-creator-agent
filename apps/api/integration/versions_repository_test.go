//go:build integration

package integration

import (
	"context"
	"testing"

	"content-creator-agent/internal/chat"
	"content-creator-agent/internal/db"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
	"gorm.io/gorm"
)

func TestVersionRepositoryOwnershipHistoryAndLocks(t *testing.T) {
	env := newTestEnv(t, nil)
	owner, other, chatID := uuid.New(), uuid.New(), uuid.New()
	for _, id := range []uuid.UUID{owner, other} {
		require.NoError(t, env.DB.Create(&db.User{ID: id, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
		id := id
		t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", id) })
	}
	require.NoError(t, env.DB.Create(&db.Chat{ID: chatID, UserID: owner, PostType: db.PostTypeSingle}).Error)
	repo := chat.NewRepository(env.DB)
	history, err := repo.ListVersions(context.Background(), owner, chatID)
	require.NoError(t, err)
	require.Empty(t, history)
	current, err := repo.GetCurrentVersion(context.Background(), owner, chatID)
	require.NoError(t, err)
	require.Nil(t, current)
	_, err = repo.ListVersions(context.Background(), other, chatID)
	require.ErrorIs(t, err, gorm.ErrRecordNotFound)

	jobID, contentID, versionID := uuid.New(), uuid.New(), uuid.New()
	require.NoError(t, env.DB.Create(&db.Job{ID: jobID, ChatID: chatID, UserID: owner, Status: db.JobStatusProcessing}).Error)
	require.NoError(t, env.DB.Create(&db.ChatContent{ID: contentID, ChatID: chatID, Role: db.ChatContentRoleAssistant, Content: "ok"}).Error)
	require.NoError(t, env.DB.Create(&db.PostVersion{ID: versionID, ChatID: chatID, JobID: jobID, AssistantContentID: contentID, DocumentS3Key: "slides/test/document.json", SchemaVersion: 1, RendererVersion: "1"}).Error)
	history, err = repo.ListVersions(context.Background(), owner, chatID)
	require.NoError(t, err)
	require.Len(t, history, 1)
	_, err = repo.GetOwnedVersion(context.Background(), other, chatID, versionID)
	require.ErrorIs(t, err, gorm.ErrRecordNotFound)
	version, err := repo.GetOwnedVersion(context.Background(), owner, chatID, versionID)
	require.NoError(t, err)
	require.Equal(t, versionID, version.ID)
	require.NoError(t, env.DB.Exec("UPDATE chats SET current_version_id = ? WHERE id = ?", versionID, chatID).Error)
	current, err = repo.GetCurrentVersion(context.Background(), owner, chatID)
	require.NoError(t, err)
	require.Equal(t, versionID, current.ID)
	require.NoError(t, env.DB.Exec("UPDATE chats SET current_version_id = NULL WHERE id = ?", chatID).Error)

	tx := env.DB.Begin()
	require.NoError(t, tx.Error)
	defer tx.Rollback()
	row, err := repo.LockOwnedChat(context.Background(), tx, owner, chatID)
	require.NoError(t, err)
	require.Nil(t, row.CurrentVersionID)
	tx2 := env.DB.Begin()
	require.NoError(t, tx2.Error)
	defer tx2.Rollback()
	require.NoError(t, tx2.Exec("SET LOCAL lock_timeout = '100ms'").Error)
	_, err = repo.LockOwnedChat(context.Background(), tx2, owner, chatID)
	require.Error(t, err)
}
