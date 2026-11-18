//go:build integration

package integration

import (
	"encoding/json"
	"net/http"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

func TestListChats_EmptyForNewUser(t *testing.T) {
	env := newTestEnv(t, noopWorker)
	token, _ := registerAndLogin(t, env)
	req, err := http.NewRequest(http.MethodGet, env.APIURL+"/chats", nil)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+token)
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusOK, res.StatusCode)
	var list []json.RawMessage
	require.NoError(t, json.NewDecoder(res.Body).Decode(&list))
	require.Len(t, list, 0)
}

func TestGetChat_Returns403IfNotOwner(t *testing.T) {
	env := newTestEnv(t, noopWorker)
	tokenA, _ := registerAndLogin(t, env)
	chatID := createChat(t, env, tokenA)

	tokenB, _ := registerAndLogin(t, env)
	req, err := http.NewRequest(http.MethodGet, env.APIURL+"/chats/"+chatID.String(), nil)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+tokenB)
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusForbidden, res.StatusCode)
}

func TestDeleteChat_RemovesFromDB(t *testing.T) {
	env := newTestEnv(t, noopWorker)
	token, _ := registerAndLogin(t, env)
	chatID := createChat(t, env, token)

	req, err := http.NewRequest(http.MethodDelete, env.APIURL+"/chats/"+chatID.String(), nil)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+token)
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusNoContent, res.StatusCode)

	req2, err := http.NewRequest(http.MethodGet, env.APIURL+"/chats/"+chatID.String(), nil)
	require.NoError(t, err)
	req2.Header.Set("Authorization", "Bearer "+token)
	res2, err := env.HTTPClient.Do(req2)
	require.NoError(t, err)
	defer res2.Body.Close()
	require.Equal(t, http.StatusNotFound, res2.StatusCode)
}

func TestChatLimit_EvictsOldestOnSixth(t *testing.T) {
	env := newTestEnv(t, noopWorker)
	token, _ := registerAndLogin(t, env)
	var firstID uuid.UUID
	for i := range 6 {
		if i > 0 {
			time.Sleep(15 * time.Millisecond)
		}
		id := createChat(t, env, token)
		if i == 0 {
			firstID = id
		}
	}

	req, err := http.NewRequest(http.MethodGet, env.APIURL+"/chats", nil)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+token)
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusOK, res.StatusCode)
	var list []struct {
		ID uuid.UUID `json:"id"`
	}
	require.NoError(t, json.NewDecoder(res.Body).Decode(&list))
	require.Len(t, list, 5)
	ids := make(map[uuid.UUID]struct{}, len(list))
	for _, c := range list {
		ids[c.ID] = struct{}{}
	}
	_, hasFirst := ids[firstID]
	require.False(t, hasFirst, "oldest chat should be evicted")
}
