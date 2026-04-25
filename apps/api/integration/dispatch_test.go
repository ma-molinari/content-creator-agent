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

func TestJobDispatch_MockWorkerComplete(t *testing.T) {
	env := newTestEnv(t, func(w http.ResponseWriter, r *http.Request, apiBase string) {
		var p jobs.DispatchPayload
		require.NoError(t, json.NewDecoder(r.Body).Decode(&p))
		go func() {
			cb := map[string]any{
				"assistantText": "Integration assistant reply",
				"artifacts": []map[string]any{
					{"s3Key": "integration/test/slide1.jpg", "slideNumber": 1},
				},
			}
			b, err := json.Marshal(cb)
			if err != nil {
				t.Logf("marshal callback: %v", err)
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
				t.Logf("callback request: %v", err)
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
	jobID := postMessage(t, env, token, chatID, "Create a carousel about testing.")

	status, _ := pollJobDone(t, env, token, chatID, jobID, 5*time.Second)
	require.Equal(t, "done", status)

	req, err := http.NewRequest(http.MethodGet, env.APIURL+"/chats/"+chatID.String(), nil)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+token)
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusOK, res.StatusCode)

	var chat struct {
		Contents []struct {
			Role    string `json:"role"`
			Content string `json:"content"`
			Images  []struct {
				S3Key string `json:"s3Key"`
			} `json:"images"`
		} `json:"contents"`
	}
	require.NoError(t, json.NewDecoder(res.Body).Decode(&chat))

	var foundAssistant bool
	for _, c := range chat.Contents {
		if c.Role != "assistant" {
			continue
		}
		foundAssistant = true
		require.Contains(t, c.Content, "Integration assistant reply")
		require.NotEmpty(t, c.Images)
		require.Equal(t, "integration/test/slide1.jpg", c.Images[0].S3Key)
	}
	require.True(t, foundAssistant, "expected assistant message with image")
}
