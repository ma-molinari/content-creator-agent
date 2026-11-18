//go:build integration

package integration

import (
	"testing"

	"content-creator-agent/internal/db"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

func TestPostVersionConstraintsAndChatDeletion(t *testing.T) {
	env := newTestEnv(t, nil)
	userID, chatID, otherChatID := uuid.New(), uuid.New(), uuid.New()
	jobID, contentID, versionID := uuid.New(), uuid.New(), uuid.New()
	user := db.User{ID: userID, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}
	require.NoError(t, env.DB.Create(&user).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", userID) })
	for _, id := range []uuid.UUID{chatID, otherChatID} {
		require.NoError(t, env.DB.Create(&db.Chat{ID: id, UserID: userID, PostType: db.PostTypeSingle}).Error)
	}
	var chat db.Chat
	require.NoError(t, env.DB.First(&chat, "id = ?", chatID).Error)
	require.Equal(t, db.PostFormatLegacy, chat.PostFormat)
	require.NoError(t, env.DB.Create(&db.Job{ID: jobID, ChatID: chatID, UserID: userID, Status: db.JobStatusProcessing}).Error)
	require.NoError(t, env.DB.Create(&db.ChatContent{ID: contentID, ChatID: chatID, Role: db.ChatContentRoleAssistant, Content: "ok"}).Error)
	version := db.PostVersion{ID: versionID, ChatID: chatID, JobID: jobID, AssistantContentID: contentID, DocumentS3Key: "slides/test/document.json", SchemaVersion: 1, RendererVersion: "1"}
	require.NoError(t, env.DB.Create(&version).Error)
	duplicate := version
	duplicate.ID = uuid.New()
	require.Error(t, env.DB.Create(&duplicate).Error)
	otherJobID, otherContentID := uuid.New(), uuid.New()
	require.NoError(t, env.DB.Create(&db.Job{ID: otherJobID, ChatID: otherChatID, UserID: userID, Status: db.JobStatusProcessing}).Error)
	require.NoError(t, env.DB.Create(&db.ChatContent{ID: otherContentID, ChatID: otherChatID, Role: db.ChatContentRoleAssistant, Content: "other"}).Error)
	crossChat := db.PostVersion{ID: uuid.New(), ChatID: otherChatID, JobID: otherJobID, AssistantContentID: otherContentID, ParentVersionID: &versionID, DocumentS3Key: "slides/other/document.json", SchemaVersion: 1, RendererVersion: "1"}
	require.Error(t, env.DB.Create(&crossChat).Error)
	require.Error(t, env.DB.Exec("UPDATE chats SET current_version_id = ? WHERE id = ?", versionID, otherChatID).Error)
	require.NoError(t, env.DB.Exec("UPDATE chats SET current_version_id = ? WHERE id = ?", versionID, chatID).Error)
	require.NoError(t, env.DB.Delete(&db.Chat{}, "id = ?", chatID).Error)
	var count int64
	require.NoError(t, env.DB.Model(&db.PostVersion{}).Where("id = ?", versionID).Count(&count).Error)
	require.Zero(t, count)
}
