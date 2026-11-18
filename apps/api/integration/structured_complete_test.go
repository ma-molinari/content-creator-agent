//go:build integration

package integration

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"strings"
	"sync"
	"testing"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

func TestStructuredCompletionSerializesFirstVersions(t *testing.T) {
	env := newTestEnv(t, nil)
	userID, chatID := uuid.New(), uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: userID, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", userID) })
	require.NoError(t, env.DB.Create(&db.Chat{ID: chatID, UserID: userID, PostType: db.PostTypeSingle, PostFormat: db.PostFormatStructuredV1}).Error)
	mode := "create"
	ids := []uuid.UUID{uuid.New(), uuid.New()}
	for _, id := range ids {
		require.NoError(t, env.DB.Create(&db.Job{ID: id, ChatID: chatID, UserID: userID, Status: db.JobStatusProcessing, PostFormat: db.PostFormatStructuredV1, GenerationMode: &mode}).Error)
	}
	type result struct {
		done, conflict bool
		err            error
	}
	results := make([]result, 2)
	var wg sync.WaitGroup
	for i, id := range ids {
		wg.Add(1)
		go func(index int, jobID uuid.UUID) {
			defer wg.Done()
			prefix := fmt.Sprintf("slides/%s/", jobID)
			html := prefix + "slide_01.html"
			results[index].done, results[index].conflict, results[index].err = jobs.CompleteStructuredReply(context.Background(), env.DB, jobID, "ok", []jobs.ArtifactRef{{S3Key: prefix + "slide_01.jpeg", HtmlS3Key: &html, SlideNumber: 1}}, jobs.StructuredArtifact{DocumentS3Key: prefix + "document.json", SchemaVersion: 1, RendererVersion: "1"}, mockStorage{})
		}(i, id)
	}
	wg.Wait()
	conflicts := 0
	for _, r := range results {
		require.NoError(t, r.err)
		require.False(t, r.done)
		if r.conflict {
			conflicts++
		}
	}
	require.Equal(t, 1, conflicts)
	var versions []db.PostVersion
	require.NoError(t, env.DB.Where("chat_id = ?", chatID).Find(&versions).Error)
	require.Len(t, versions, 1)
	var chat db.Chat
	require.NoError(t, env.DB.First(&chat, "id = ?", chatID).Error)
	require.Equal(t, versions[0].ID, *chat.CurrentVersionID)
	var failed db.Job
	require.NoError(t, env.DB.Where("chat_id = ? AND status = ?", chatID, db.JobStatusFailed).First(&failed).Error)
	require.Equal(t, "VERSION_CONFLICT", *failed.ErrorCode)
	winner := versions[0].JobID
	prefix := fmt.Sprintf("slides/%s/", winner)
	html := prefix + "slide_01.html"
	done, conflict, err := jobs.CompleteStructuredReply(context.Background(), env.DB, winner, "ok", []jobs.ArtifactRef{{S3Key: prefix + "slide_01.jpeg", HtmlS3Key: &html, SlideNumber: 1}}, jobs.StructuredArtifact{DocumentS3Key: prefix + "document.json", SchemaVersion: 1, RendererVersion: "1"}, mockStorage{})
	require.NoError(t, err)
	require.True(t, done)
	require.False(t, conflict)
	editID := uuid.New()
	editMode := "edit"
	require.NoError(t, env.DB.Create(&db.Job{ID: editID, ChatID: chatID, UserID: userID, Status: db.JobStatusProcessing, PostFormat: db.PostFormatStructuredV1, GenerationMode: &editMode, ExpectedVersionID: chat.CurrentVersionID}).Error)
	prefix = fmt.Sprintf("slides/%s/", editID)
	html = prefix + "slide_01.html"
	artifacts := []jobs.ArtifactRef{{S3Key: prefix + "slide_01.jpeg", HtmlS3Key: &html, SlideNumber: 1}}
	_, _, err = jobs.CompleteStructuredReply(context.Background(), env.DB, editID, "ok", artifacts, jobs.StructuredArtifact{DocumentS3Key: "slides/other/document.json", SchemaVersion: 1, RendererVersion: "1"}, mockStorage{})
	require.Error(t, err)
	_, err = jobs.CompleteAssistantReply(context.Background(), env.DB, editID, "ok", artifacts, mockStorage{})
	require.Error(t, err)
	var pending db.Job
	require.NoError(t, env.DB.First(&pending, "id = ?", editID).Error)
	require.Equal(t, db.JobStatusProcessing, pending.Status)
}

func TestStructuredMessageFailsClosedBeforeMutation(t *testing.T) {
	env := newTestEnv(t, nil)
	token, userID := registerAndLogin(t, env)
	chatID := createChat(t, env, token)
	require.NoError(t, env.DB.Model(&db.Chat{}).Where("id = ? AND user_id = ?", chatID, userID).Update("post_format", db.PostFormatStructuredV1).Error)
	legacyReq, err := http.NewRequest(http.MethodPost, env.APIURL+"/chats/"+chatID.String()+"/messages", strings.NewReader(`{"content":"crie","mode":"create"}`))
	require.NoError(t, err)
	legacyReq.Header.Set("Authorization", "Bearer "+token)
	legacyReq.Header.Set("Content-Type", "application/json")
	legacyRes, err := env.HTTPClient.Do(legacyReq)
	require.NoError(t, err)
	legacyRes.Body.Close()
	require.Equal(t, http.StatusUpgradeRequired, legacyRes.StatusCode)
	cases := []struct {
		body     string
		expected int
		code     string
	}{
		{`{"content":"crie"}`, 400, "MODE_REQUIRED"},
		{`{"content":"crie","mode":"create"}`, 503, "STRUCTURED_UNAVAILABLE"},
		{`{"content":"edite","mode":"edit","baseVersionId":"00000000-0000-0000-0000-000000000001"}`, 409, "VERSION_CONFLICT"},
	}
	for _, tc := range cases {
		req, err := http.NewRequest(http.MethodPost, env.APIURL+"/chats/"+chatID.String()+"/messages", strings.NewReader(tc.body))
		require.NoError(t, err)
		req.Header.Set("Authorization", "Bearer "+token)
		req.Header.Set("X-Post-Client-Version", "1")
		req.Header.Set("Content-Type", "application/json")
		res, err := env.HTTPClient.Do(req)
		require.NoError(t, err)
		body, err := io.ReadAll(res.Body)
		res.Body.Close()
		require.NoError(t, err)
		require.Equal(t, tc.expected, res.StatusCode, string(body))
		require.Contains(t, string(body), tc.code)
	}
	var form bytes.Buffer
	writer := multipart.NewWriter(&form)
	require.NoError(t, writer.WriteField("content", "crie"))
	require.NoError(t, writer.WriteField("mode", "create"))
	require.NoError(t, writer.Close())
	req, err := http.NewRequest(http.MethodPost, env.APIURL+"/chats/"+chatID.String()+"/messages", &form)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("X-Post-Client-Version", "1")
	req.Header.Set("Content-Type", writer.FormDataContentType())
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	body, err := io.ReadAll(res.Body)
	res.Body.Close()
	require.NoError(t, err)
	require.Equal(t, http.StatusServiceUnavailable, res.StatusCode, string(body))
	require.Contains(t, string(body), "STRUCTURED_UNAVAILABLE")
	var messages, jobCount int64
	require.NoError(t, env.DB.Model(&db.ChatContent{}).Where("chat_id = ?", chatID).Count(&messages).Error)
	require.NoError(t, env.DB.Model(&db.Job{}).Where("chat_id = ?", chatID).Count(&jobCount).Error)
	require.Zero(t, messages)
	require.Zero(t, jobCount)
}

func TestStructuredChatExposesVersionMetadataToOwner(t *testing.T) {
	env := newTestEnv(t, nil)
	token, userID := registerAndLogin(t, env)
	chatID := createChat(t, env, token)
	require.NoError(t, env.DB.Model(&db.Chat{}).Where("id = ?", chatID).Update("post_format", db.PostFormatStructuredV1).Error)
	jobID, contentID, versionID := uuid.New(), uuid.New(), uuid.New()
	require.NoError(t, env.DB.Create(&db.Job{ID: jobID, ChatID: chatID, UserID: userID, Status: db.JobStatusDone, PostFormat: db.PostFormatStructuredV1}).Error)
	require.NoError(t, env.DB.Create(&db.ChatContent{ID: contentID, ChatID: chatID, Role: db.ChatContentRoleAssistant, Content: "ok"}).Error)
	require.NoError(t, env.DB.Create(&db.PostVersion{ID: versionID, ChatID: chatID, JobID: jobID, AssistantContentID: contentID, DocumentS3Key: "slides/test/document.json", SchemaVersion: 1, RendererVersion: "1"}).Error)
	require.NoError(t, env.DB.Model(&db.Chat{}).Where("id = ?", chatID).Update("current_version_id", versionID).Error)
	req, err := http.NewRequest(http.MethodGet, env.APIURL+"/chats/"+chatID.String(), nil)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("X-Post-Client-Version", "1")
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	body, err := io.ReadAll(res.Body)
	require.NoError(t, err)
	require.Equal(t, http.StatusOK, res.StatusCode, string(body))
	require.Contains(t, string(body), `"postFormat":"structured_v1"`)
	require.Contains(t, string(body), `"currentVersionId":"`+versionID.String()+`"`)
	require.Contains(t, string(body), `"versionId":"`+versionID.String()+`"`)
	require.NotContains(t, string(body), "documentS3Key")
}
