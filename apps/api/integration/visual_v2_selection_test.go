//go:build integration

package integration

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"content-creator-agent/internal/chat"
	"content-creator-agent/internal/config"
	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

type visualCaptureWorker struct{ payload jobs.DispatchPayload }

func (w *visualCaptureWorker) SupportsStructured(context.Context) bool { return true }
func (w *visualCaptureWorker) SupportsStructuredV2(_ context.Context, read int) bool {
	return read == 0
}
func (w *visualCaptureWorker) DispatchJob(_ context.Context, payload jobs.DispatchPayload) error {
	w.payload = payload
	return nil
}

func TestVisualV2HTTPDispatchUsesPersistedTarget(t *testing.T) {
	env := newTestEnv(t, nil)
	worker := &visualCaptureWorker{}
	cfg := &config.Config{JWTSecret: testJWTSecret, JWTRefreshSecret: testJWTRefreshSecret, WorkerAPIKey: IntegrationWorkerAPIKey, StructuredVisualV2Enabled: true}
	server := httptest.NewServer(buildEcho(env.DB, cfg, worker, mockStorage{}))
	defer server.Close()
	env.APIURL = server.URL
	token, user := registerAndLogin(t, env)
	env.putTestProfile(t, token)
	chatID := uuid.New()
	require.NoError(t, env.DB.Create(&db.Chat{ID: chatID, UserID: user, PostType: db.PostTypeSingle, PostFormat: db.PostFormatStructuredV1}).Error)
	req, err := http.NewRequest(http.MethodPost, env.APIURL+"/chats/"+chatID.String()+"/messages", strings.NewReader(`{"content":"crie um post","mode":"create"}`))
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Post-Client-Version", "1")
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusAccepted, res.StatusCode)
	var response struct {
		JobID uuid.UUID `json:"jobId"`
	}
	require.NoError(t, json.NewDecoder(res.Body).Decode(&response))
	var saved db.Job
	require.NoError(t, env.DB.First(&saved, "id = ?", response.JobID).Error)
	require.Equal(t, 2, saved.StructuredTargetSchema())
	require.NotNil(t, worker.payload.TargetSchemaVersion)
	require.Equal(t, 2, *worker.payload.TargetSchemaVersion)
}

func TestVisualV2SchemaSelectionIsAtomic(t *testing.T) {
	env := newTestEnv(t, nil)
	ctx := context.Background()
	user := uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: user, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", user) })
	for _, tc := range []struct {
		name                     string
		base, want               int
		mode                     string
		enabled, disabled, ready bool
		read                     int
		fails                    bool
	}{
		{"create flag off", 0, 1, "create", false, false, false, 0, false},
		{"create flag on", 0, 2, "create", true, false, true, 0, false},
		{"edit v1 flag off", 1, 1, "edit", false, false, false, 0, false},
		{"promote v1", 1, 2, "edit", true, false, true, 1, false},
		{"edit v2 after rollback", 2, 2, "edit", false, false, true, 2, false},
		{"new v1 root after v2", 2, 1, "create", false, false, false, 0, false},
		{"unavailable v2", 1, 0, "edit", true, false, false, 1, true},
		{"incident block", 2, 0, "edit", false, true, true, 0, true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			chatID := uuid.New()
			require.NoError(t, env.DB.Create(&db.Chat{ID: chatID, UserID: user, PostType: db.PostTypeSingle, PostFormat: db.PostFormatStructuredV1}).Error)
			var baseID *uuid.UUID
			if tc.base != 0 {
				jobID, contentID, versionID := uuid.New(), uuid.New(), uuid.New()
				require.NoError(t, env.DB.Create(&db.Job{ID: jobID, ChatID: chatID, UserID: user, Status: db.JobStatusDone, PostFormat: db.PostFormatStructuredV1}).Error)
				require.NoError(t, env.DB.Create(&db.ChatContent{ID: contentID, ChatID: chatID, Role: db.ChatContentRoleAssistant, Content: "anterior"}).Error)
				require.NoError(t, env.DB.Create(&db.PostVersion{ID: versionID, ChatID: chatID, JobID: jobID, AssistantContentID: contentID, DocumentS3Key: "slides/base/document.json", SchemaVersion: tc.base, RendererVersion: "1"}).Error)
				require.NoError(t, env.DB.Model(&db.Chat{}).Where("id = ?", chatID).Update("current_version_id", versionID).Error)
				baseID = &versionID
			}
			job := &db.Job{ID: uuid.New(), ChatID: chatID, UserID: user, Status: db.JobStatusProcessing}
			message := &db.ChatContent{ID: uuid.New(), ChatID: chatID, Role: db.ChatContentRoleUser, Content: "mensagem"}
			calls := []int{}
			check := func(_ context.Context, read int) bool { calls = append(calls, read); return tc.ready }
			requested := baseID
			if tc.mode == "create" {
				requested = nil
			}
			_, err := chat.NewRepository(env.DB).CreateStructuredMessageAndJob(ctx, user, message, job, tc.mode, requested, nil, nil, tc.enabled, tc.disabled, check)
			if tc.fails {
				require.ErrorIs(t, err, chat.ErrStructuredUnavailable)
				var count int64
				require.NoError(t, env.DB.Model(&db.ChatContent{}).Where("id = ?", message.ID).Count(&count).Error)
				require.Zero(t, count)
			} else {
				require.NoError(t, err)
				var saved db.Job
				require.NoError(t, env.DB.First(&saved, "id = ?", job.ID).Error)
				require.Equal(t, tc.want, saved.StructuredTargetSchema())
				if baseID != nil {
					require.Equal(t, *baseID, *saved.ExpectedVersionID)
				}
			}
			if tc.want == 2 || (tc.fails && !tc.disabled) {
				require.Equal(t, []int{tc.read}, calls)
			} else {
				require.Empty(t, calls)
			}
		})
	}
}
