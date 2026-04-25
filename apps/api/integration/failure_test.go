//go:build integration

package integration

import (
	"bytes"
	"encoding/json"
	"net/http"
	"testing"
	"time"

	"content-creator-agent/internal/jobs"

	"github.com/stretchr/testify/require"
)

func TestJobDispatch_WorkerCallbackError(t *testing.T) {
	env := newTestEnv(t, func(w http.ResponseWriter, r *http.Request, apiBase string) {
		var p jobs.DispatchPayload
		require.NoError(t, json.NewDecoder(r.Body).Decode(&p))
		go func() {
			errStr := "LLM indisponível"
			cb := map[string]any{
				"error": errStr,
			}
			b, err := json.Marshal(cb)
			if err != nil {
				t.Logf("marshal: %v", err)
				return
			}
			req, err := http.NewRequest(http.MethodPost, apiBase+"/internal/jobs/"+p.JobID.String()+"/complete", bytes.NewReader(b))
			if err != nil {
				t.Logf("new request: %v", err)
				return
			}
			req.Header.Set("Content-Type", "application/json")
			req.Header.Set("X-Worker-API-Key", IntegrationWorkerAPIKey)
			cli := &http.Client{Timeout: 10 * time.Second}
			resp, err := cli.Do(req)
			if err != nil {
				t.Logf("callback: %v", err)
				return
			}
			if resp != nil {
				_ = resp.Body.Close()
			}
		}()
		w.WriteHeader(http.StatusAccepted)
	})

	token, _ := registerAndLogin(t, env)
	env.putTestProfile(t, token)
	chatID := createChat(t, env, token)
	jobID := postMessage(t, env, token, chatID, "This should fail at callback.")

	status, errMsg := pollJobDone(t, env, token, chatID, jobID, 5*time.Second)
	require.Equal(t, "failed", status)
	require.NotNil(t, errMsg)
	require.Contains(t, *errMsg, "LLM")
}

func TestJobDispatch_WorkerRejectsDispatch(t *testing.T) {
	env := newTestEnv(t, func(w http.ResponseWriter, _ *http.Request, _ string) {
		http.Error(w, "internal error", http.StatusInternalServerError)
	})

	token, _ := registerAndLogin(t, env)
	env.putTestProfile(t, token)
	chatID := createChat(t, env, token)

	body := map[string]string{"content": "Dispatch will fail."}
	b, _ := json.Marshal(body)
	req, err := http.NewRequest(http.MethodPost, env.APIURL+"/chats/"+chatID.String()+"/messages", bytes.NewReader(b))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+token)
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusBadGateway, res.StatusCode)

	jobID := lastJobIDForChat(t, env, chatID)
	status, _ := getJobStatus(t, env, token, chatID, jobID)
	require.Equal(t, "failed", status)
}

func TestCallback_InvalidS3Key_Returns400(t *testing.T) {
	env := newTestEnv(t, func(w http.ResponseWriter, _ *http.Request, _ string) {
		w.WriteHeader(http.StatusAccepted)
	})

	token, _ := registerAndLogin(t, env)
	env.putTestProfile(t, token)
	chatID := createChat(t, env, token)
	jobID := postMessage(t, env, token, chatID, "trigger job for invalid s3 key test")

	cb := map[string]any{
		"assistantText": "should not persist",
		"artifacts": []map[string]any{
			{"s3Key": "integration/evil/../other-job/slide1.jpg", "slideNumber": 1},
		},
	}
	b, err := json.Marshal(cb)
	require.NoError(t, err)
	req, err := http.NewRequest(
		http.MethodPost,
		env.APIURL+"/internal/jobs/"+jobID.String()+"/complete",
		bytes.NewReader(b),
	)
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Worker-API-Key", IntegrationWorkerAPIKey)
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusBadRequest, res.StatusCode)

	status, _ := getJobStatus(t, env, token, chatID, jobID)
	require.NotEqual(t, "done", status)
}

func TestCallback_MissingAssistantText(t *testing.T) {
	env := newTestEnv(t, func(w http.ResponseWriter, _ *http.Request, _ string) {
		w.WriteHeader(http.StatusAccepted)
	})

	token, _ := registerAndLogin(t, env)
	env.putTestProfile(t, token)
	chatID := createChat(t, env, token)
	jobID := postMessage(t, env, token, chatID, "trigger job for callback test")

	req, err := http.NewRequest(
		http.MethodPost,
		env.APIURL+"/internal/jobs/"+jobID.String()+"/complete",
		bytes.NewReader([]byte(`{}`)),
	)
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Worker-API-Key", IntegrationWorkerAPIKey)
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusBadRequest, res.StatusCode)
}
