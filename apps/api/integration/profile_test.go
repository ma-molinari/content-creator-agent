//go:build integration

package integration

import (
	"bytes"
	"encoding/json"
	"net/http"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestProfile_getEmptyThenPutAndSetupStatus(t *testing.T) {
	env := newTestEnv(t, nil)
	token, _ := registerAndLogin(t, env)

	req, err := http.NewRequest(http.MethodGet, env.APIURL+"/profile", nil)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+token)
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusOK, res.StatusCode)
	var get1 struct {
		AuditText  string `json:"auditText"`
		BrandText  string `json:"brandText"`
		Configured bool   `json:"configured"`
	}
	require.NoError(t, json.NewDecoder(res.Body).Decode(&get1))
	require.False(t, get1.Configured)

	req2, err := http.NewRequest(http.MethodGet, env.APIURL+"/setup/status", nil)
	require.NoError(t, err)
	req2.Header.Set("Authorization", "Bearer "+token)
	res2, err := env.HTTPClient.Do(req2)
	require.NoError(t, err)
	defer res2.Body.Close()
	require.Equal(t, http.StatusOK, res2.StatusCode)
	var st1 struct {
		Configured bool `json:"configured"`
	}
	require.NoError(t, json.NewDecoder(res2.Body).Decode(&st1))
	require.False(t, st1.Configured)

	body := map[string]string{"auditText": "audit content", "brandText": "brand content"}
	b, _ := json.Marshal(body)
	req3, err := http.NewRequest(http.MethodPut, env.APIURL+"/profile", bytes.NewReader(b))
	require.NoError(t, err)
	req3.Header.Set("Content-Type", "application/json")
	req3.Header.Set("Authorization", "Bearer "+token)
	res3, err := env.HTTPClient.Do(req3)
	require.NoError(t, err)
	defer res3.Body.Close()
	require.Equal(t, http.StatusOK, res3.StatusCode)
	var putResp struct {
		Configured bool `json:"configured"`
	}
	require.NoError(t, json.NewDecoder(res3.Body).Decode(&putResp))
	require.True(t, putResp.Configured)

	req4, err := http.NewRequest(http.MethodGet, env.APIURL+"/setup/status", nil)
	require.NoError(t, err)
	req4.Header.Set("Authorization", "Bearer "+token)
	res4, err := env.HTTPClient.Do(req4)
	require.NoError(t, err)
	defer res4.Body.Close()
	require.Equal(t, http.StatusOK, res4.StatusCode)
	var st2 struct {
		Configured bool `json:"configured"`
	}
	require.NoError(t, json.NewDecoder(res4.Body).Decode(&st2))
	require.True(t, st2.Configured)
}
