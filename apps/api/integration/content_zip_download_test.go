//go:build integration

package integration

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"testing"

	"content-creator-agent/internal/db"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

func TestDownloadContentZip_ReturnsZIPWhenImagesExist(t *testing.T) {
	env := newTestEnv(t, noopWorker)
	token, _ := registerAndLogin(t, env)
	chatID := createChat(t, env, token)

	content := db.ChatContent{
		ChatID:  chatID,
		Role:    db.ChatContentRoleAssistant,
		Content: "assistant turn",
	}
	require.NoError(t, env.DB.WithContext(context.Background()).Create(&content).Error)

	img := db.ChatContentImage{
		ChatContentID: content.ID,
		S3Key:         "slides/" + uuid.NewString() + "/slide-001.jpg",
		URL:           "https://integration.test/preview",
		SlideNumber:   1,
	}
	require.NoError(t, env.DB.WithContext(context.Background()).Create(&img).Error)

	req, err := http.NewRequest(
		http.MethodGet,
		env.APIURL+"/chats/"+chatID.String()+"/contents/"+content.ID.String()+"/download",
		nil,
	)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+token)
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusOK, res.StatusCode)
	body, err := io.ReadAll(res.Body)
	require.NoError(t, err)
	require.True(t, bytes.HasPrefix(body, []byte{'P', 'K', 3, 4}), "response should be a ZIP")
}

func TestDownloadContentZip_ReturnsNoFilesWhenAssistantHasNoImages(t *testing.T) {
	env := newTestEnv(t, noopWorker)
	token, _ := registerAndLogin(t, env)
	chatID := createChat(t, env, token)

	content := db.ChatContent{
		ChatID:  chatID,
		Role:    db.ChatContentRoleAssistant,
		Content: "no slides",
	}
	require.NoError(t, env.DB.WithContext(context.Background()).Create(&content).Error)

	req, err := http.NewRequest(
		http.MethodGet,
		env.APIURL+"/chats/"+chatID.String()+"/contents/"+content.ID.String()+"/download",
		nil,
	)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+token)
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusNotFound, res.StatusCode)
	var out struct {
		Message string `json:"message"`
	}
	require.NoError(t, json.NewDecoder(res.Body).Decode(&out))
	require.Equal(t, "no files", out.Message)
}
