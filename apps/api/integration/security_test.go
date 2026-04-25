//go:build integration

package integration

import (
	"bytes"
	"encoding/json"
	"net/http"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

func TestProtectedEndpoint_NoToken_Returns401(t *testing.T) {
	env := newTestEnv(t, noopWorker)
	req, err := http.NewRequest(http.MethodGet, env.APIURL+"/me", nil)
	require.NoError(t, err)
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusUnauthorized, res.StatusCode)
}

func TestInternalCallback_WrongAPIKey_Returns401(t *testing.T) {
	env := newTestEnv(t, noopWorker)
	jobID := uuid.New()
	body := map[string]string{"assistantText": "x"}
	b, err := json.Marshal(body)
	require.NoError(t, err)
	req, err := http.NewRequest(http.MethodPost, env.APIURL+"/internal/jobs/"+jobID.String()+"/complete", bytes.NewReader(b))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Worker-API-Key", "wrong-key")
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusUnauthorized, res.StatusCode)
}

func TestCORSHeaders_Present(t *testing.T) {
	env := newTestEnvWithCORS(t, noopWorker, []string{"http://127.0.0.1:4173"})
	req, err := http.NewRequest(http.MethodOptions, env.APIURL+"/health", nil)
	require.NoError(t, err)
	req.Header.Set("Origin", "http://127.0.0.1:4173")
	req.Header.Set("Access-Control-Request-Method", "GET")
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusNoContent, res.StatusCode)
	require.Equal(t, "http://127.0.0.1:4173", res.Header.Get("Access-Control-Allow-Origin"))
	require.Equal(t, "true", res.Header.Get("Access-Control-Allow-Credentials"))
}
