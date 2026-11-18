//go:build integration

package integration

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"testing"

	"content-creator-agent/internal/config"
	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

type httpStructuredWorker struct{ payloads []jobs.DispatchPayload }

func (w *httpStructuredWorker) SupportsStructured(context.Context) bool { return true }
func (w *httpStructuredWorker) DispatchJob(_ context.Context, p jobs.DispatchPayload) error {
	w.payloads = append(w.payloads, p)
	return nil
}

func TestStructuredHTTPCreateAndMultipartEdit(t *testing.T) {
	env := newTestEnv(t, nil)
	worker := &httpStructuredWorker{}
	cfg := &config.Config{JWTSecret: testJWTSecret, JWTRefreshSecret: testJWTRefreshSecret, WorkerAPIKey: IntegrationWorkerAPIKey, StructuredPostsEnabled: true}
	server := httptest.NewServer(buildEcho(env.DB, cfg, worker, mockStorage{}))
	t.Cleanup(server.Close)
	env.APIURL = server.URL
	token, uid := registerAndLogin(t, env)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", uid) })
	env.putTestProfile(t, token)
	request := func(method, path, contentType string, body *bytes.Buffer, clientVersion bool) *http.Response {
		t.Helper()
		if body == nil {
			body = &bytes.Buffer{}
		}
		req, err := http.NewRequest(method, env.APIURL+path, body)
		require.NoError(t, err)
		req.Header.Set("Authorization", "Bearer "+token)
		if contentType != "" {
			req.Header.Set("Content-Type", contentType)
		}
		if clientVersion {
			req.Header.Set("X-Post-Client-Version", "1")
		}
		res, err := env.HTTPClient.Do(req)
		require.NoError(t, err)
		return res
	}
	res := request(http.MethodPost, "/chats", "application/json", bytes.NewBufferString(`{"postType":"single"}`), true)
	require.Equal(t, http.StatusCreated, res.StatusCode)
	var created struct {
		ID         uuid.UUID `json:"id"`
		PostFormat string    `json:"postFormat"`
	}
	require.NoError(t, json.NewDecoder(res.Body).Decode(&created))
	res.Body.Close()
	require.Equal(t, "structured_v1", created.PostFormat)
	path := "/chats/" + created.ID.String()
	res = request(http.MethodGet, path, "", nil, false)
	require.Equal(t, http.StatusUpgradeRequired, res.StatusCode)
	res.Body.Close()
	res = request(http.MethodPost, path+"/messages", "application/json", bytes.NewBufferString(`{"content":"Crie","mode":"create"}`), true)
	require.Equal(t, http.StatusAccepted, res.StatusCode)
	var create struct {
		JobID uuid.UUID `json:"jobId"`
	}
	require.NoError(t, json.NewDecoder(res.Body).Decode(&create))
	res.Body.Close()
	complete := func(id uuid.UUID) {
		t.Helper()
		prefix := fmt.Sprintf("slides/%s/", id)
		payload := map[string]interface{}{"assistantText": "ok", "artifacts": []map[string]interface{}{{"s3Key": prefix + "slide_01.jpeg", "htmlS3Key": prefix + "slide_01.html", "slideNumber": 1}}, "structured": map[string]interface{}{"documentS3Key": prefix + "document.json", "schemaVersion": 1, "rendererVersion": "1"}}
		raw, err := json.Marshal(payload)
		require.NoError(t, err)
		req, err := http.NewRequest(http.MethodPost, env.APIURL+"/internal/jobs/"+id.String()+"/complete", bytes.NewReader(raw))
		require.NoError(t, err)
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("X-Worker-API-Key", IntegrationWorkerAPIKey)
		response, err := env.HTTPClient.Do(req)
		require.NoError(t, err)
		response.Body.Close()
		require.Equal(t, http.StatusNoContent, response.StatusCode)
	}
	complete(create.JobID)
	res = request(http.MethodGet, path, "", nil, true)
	require.Equal(t, http.StatusOK, res.StatusCode)
	var current struct {
		CurrentVersionID uuid.UUID `json:"currentVersionId"`
	}
	require.NoError(t, json.NewDecoder(res.Body).Decode(&current))
	res.Body.Close()
	require.NotEqual(t, uuid.Nil, current.CurrentVersionID)
	var form bytes.Buffer
	writer := multipart.NewWriter(&form)
	require.NoError(t, writer.WriteField("content", "Edite"))
	require.NoError(t, writer.WriteField("mode", "edit"))
	require.NoError(t, writer.WriteField("baseVersionId", current.CurrentVersionID.String()))
	require.NoError(t, writer.Close())
	res = request(http.MethodPost, path+"/messages", writer.FormDataContentType(), &form, true)
	require.Equal(t, http.StatusAccepted, res.StatusCode)
	var edit struct {
		JobID uuid.UUID `json:"jobId"`
	}
	require.NoError(t, json.NewDecoder(res.Body).Decode(&edit))
	res.Body.Close()
	require.Len(t, worker.payloads, 2)
	require.Equal(t, "edit", worker.payloads[1].GenerationMode)
	require.Equal(t, current.CurrentVersionID, *worker.payloads[1].BaseVersionID)
	complete(edit.JobID)
	var versions []db.PostVersion
	require.NoError(t, env.DB.Where("chat_id = ?", created.ID).Find(&versions).Error)
	require.Len(t, versions, 2)
	var edited db.PostVersion
	require.NoError(t, env.DB.Where("job_id = ?", edit.JobID).First(&edited).Error)
	require.Equal(t, current.CurrentVersionID, *edited.ParentVersionID)
}
