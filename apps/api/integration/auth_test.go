//go:build integration

package integration

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/cookiejar"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

func noopWorker(w http.ResponseWriter, r *http.Request, apiBase string) {
	w.WriteHeader(http.StatusOK)
}

func TestRegister_Returns201WithSecurityKey(t *testing.T) {
	env := newTestEnv(t, noopWorker)
	email := uuid.New().String() + "@integration.test"
	body := map[string]string{"email": email, "password": "password123"}
	b, err := json.Marshal(body)
	require.NoError(t, err)
	req, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/register", bytes.NewReader(b))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusCreated, res.StatusCode)
	var out struct {
		SecurityKey string `json:"securityKey"`
	}
	require.NoError(t, json.NewDecoder(res.Body).Decode(&out))
	require.NotEmpty(t, out.SecurityKey)
}

func TestRegister_DuplicateEmail_Returns409(t *testing.T) {
	env := newTestEnv(t, noopWorker)
	email := uuid.New().String() + "@integration.test"
	regBody := map[string]string{"email": email, "password": "password123"}
	regJSON, err := json.Marshal(regBody)
	require.NoError(t, err)
	req, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/register", bytes.NewReader(regJSON))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusCreated, res.StatusCode)

	req2, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/register", bytes.NewReader(regJSON))
	require.NoError(t, err)
	req2.Header.Set("Content-Type", "application/json")
	res2, err := env.HTTPClient.Do(req2)
	require.NoError(t, err)
	defer res2.Body.Close()
	require.Equal(t, http.StatusConflict, res2.StatusCode)
}

func TestLogin_WrongPassword_Returns401(t *testing.T) {
	env := newTestEnv(t, noopWorker)
	email := uuid.New().String() + "@integration.test"
	regBody := map[string]string{"email": email, "password": "password123"}
	regJSON, err := json.Marshal(regBody)
	require.NoError(t, err)
	req, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/register", bytes.NewReader(regJSON))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusCreated, res.StatusCode)

	loginBody := map[string]string{"email": email, "password": "wrong-password"}
	loginJSON, err := json.Marshal(loginBody)
	require.NoError(t, err)
	req2, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/login", bytes.NewReader(loginJSON))
	require.NoError(t, err)
	req2.Header.Set("Content-Type", "application/json")
	res2, err := env.HTTPClient.Do(req2)
	require.NoError(t, err)
	defer res2.Body.Close()
	require.Equal(t, http.StatusUnauthorized, res2.StatusCode)
}

func TestRefresh_ValidCookie_Returns200(t *testing.T) {
	env := newTestEnv(t, noopWorker)
	jar, err := cookiejar.New(nil)
	require.NoError(t, err)
	client := &http.Client{Jar: jar, Timeout: env.HTTPClient.Timeout}

	email := uuid.New().String() + "@integration.test"
	regBody := map[string]string{"email": email, "password": "password123"}
	regJSON, err := json.Marshal(regBody)
	require.NoError(t, err)
	req, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/register", bytes.NewReader(regJSON))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	res, err := client.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusCreated, res.StatusCode)

	loginBody := map[string]string{"email": email, "password": "password123"}
	loginJSON, err := json.Marshal(loginBody)
	require.NoError(t, err)
	req2, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/login", bytes.NewReader(loginJSON))
	require.NoError(t, err)
	req2.Header.Set("Content-Type", "application/json")
	res2, err := client.Do(req2)
	require.NoError(t, err)
	defer res2.Body.Close()
	require.Equal(t, http.StatusOK, res2.StatusCode)

	req3, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/refresh", nil)
	require.NoError(t, err)
	res3, err := client.Do(req3)
	require.NoError(t, err)
	defer res3.Body.Close()
	require.Equal(t, http.StatusOK, res3.StatusCode)
	var refreshResp struct {
		AccessToken string `json:"accessToken"`
	}
	require.NoError(t, json.NewDecoder(res3.Body).Decode(&refreshResp))
	require.NotEmpty(t, refreshResp.AccessToken)
}

func TestLogout_ClearsCookie_ThenRefreshUnauthorized(t *testing.T) {
	env := newTestEnv(t, noopWorker)
	jar, err := cookiejar.New(nil)
	require.NoError(t, err)
	client := &http.Client{Jar: jar, Timeout: env.HTTPClient.Timeout}

	email := uuid.New().String() + "@integration.test"
	regBody := map[string]string{"email": email, "password": "password123"}
	regJSON, err := json.Marshal(regBody)
	require.NoError(t, err)
	req, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/register", bytes.NewReader(regJSON))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	res, err := client.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusCreated, res.StatusCode)

	loginBody := map[string]string{"email": email, "password": "password123"}
	loginJSON, err := json.Marshal(loginBody)
	require.NoError(t, err)
	req2, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/login", bytes.NewReader(loginJSON))
	require.NoError(t, err)
	req2.Header.Set("Content-Type", "application/json")
	res2, err := client.Do(req2)
	require.NoError(t, err)
	defer res2.Body.Close()
	require.Equal(t, http.StatusOK, res2.StatusCode)

	reqLogout, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/logout", nil)
	require.NoError(t, err)
	resLogout, err := client.Do(reqLogout)
	require.NoError(t, err)
	defer resLogout.Body.Close()
	require.Equal(t, http.StatusNoContent, resLogout.StatusCode)

	reqRefresh, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/refresh", nil)
	require.NoError(t, err)
	resRefresh, err := client.Do(reqRefresh)
	require.NoError(t, err)
	defer resRefresh.Body.Close()
	require.Equal(t, http.StatusUnauthorized, resRefresh.StatusCode)
}

func TestRecoverPassword_WrongKey_Returns200LikeSuccess(t *testing.T) {
	env := newTestEnv(t, noopWorker)
	email := uuid.New().String() + "@integration.test"
	regBody := map[string]string{"email": email, "password": "password123"}
	regJSON, err := json.Marshal(regBody)
	require.NoError(t, err)
	req, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/register", bytes.NewReader(regJSON))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusCreated, res.StatusCode)

	body := map[string]string{
		"email":       email,
		"securityKey": "not-the-real-key",
		"newPassword": "newpassword12",
	}
	b, err := json.Marshal(body)
	require.NoError(t, err)
	req2, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/recover-password", bytes.NewReader(b))
	require.NoError(t, err)
	req2.Header.Set("Content-Type", "application/json")
	res2, err := env.HTTPClient.Do(req2)
	require.NoError(t, err)
	defer res2.Body.Close()
	require.Equal(t, http.StatusOK, res2.StatusCode)
	var out struct {
		Success bool `json:"success"`
	}
	require.NoError(t, json.NewDecoder(res2.Body).Decode(&out))
	require.True(t, out.Success)

	loginJSON, err := json.Marshal(map[string]string{"email": email, "password": "password123"})
	require.NoError(t, err)
	req3, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/login", bytes.NewReader(loginJSON))
	require.NoError(t, err)
	req3.Header.Set("Content-Type", "application/json")
	res3, err := env.HTTPClient.Do(req3)
	require.NoError(t, err)
	defer res3.Body.Close()
	require.Equal(t, http.StatusOK, res3.StatusCode)
}

func TestRecoverPassword_UnknownEmail_Returns200SameBody(t *testing.T) {
	env := newTestEnv(t, noopWorker)
	body := map[string]string{
		"email":       uuid.New().String() + "@integration.test",
		"securityKey": "any-key",
		"newPassword": "newpassword12",
	}
	b, err := json.Marshal(body)
	require.NoError(t, err)
	req, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/recover-password", bytes.NewReader(b))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusOK, res.StatusCode)
	var out struct {
		Success bool `json:"success"`
	}
	require.NoError(t, json.NewDecoder(res.Body).Decode(&out))
	require.True(t, out.Success)
}
