//go:build integration

package integration

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"

	"content-creator-agent/internal/config"
	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"content-creator-agent/internal/storage"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

type fileArtifactStore struct{ root string }

func (s fileArtifactStore) file(key string) string {
	return filepath.Join(s.root, filepath.FromSlash(key))
}
func (s fileArtifactStore) Upload(_ context.Context, key string, data []byte) error {
	if err := os.MkdirAll(filepath.Dir(s.file(key)), 0755); err != nil {
		return err
	}
	return os.WriteFile(s.file(key), data, 0600)
}
func (s fileArtifactStore) GetSignedURL(_ context.Context, key string, _ time.Duration) (string, error) {
	return "https://integration.test/" + key, nil
}
func (s fileArtifactStore) HeadObject(_ context.Context, key string) error {
	_, err := os.Stat(s.file(key))
	if os.IsNotExist(err) {
		return storage.ErrObjectNotFound
	}
	return err
}
func (s fileArtifactStore) GetObject(_ context.Context, key string) ([]byte, error) {
	data, err := os.ReadFile(s.file(key))
	if os.IsNotExist(err) {
		return nil, storage.ErrObjectNotFound
	}
	return data, err
}
func (s fileArtifactStore) GetObjectLimited(ctx context.Context, key string, max int64) ([]byte, string, error) {
	data, err := s.GetObject(ctx, key)
	if err != nil {
		return nil, "", err
	}
	if int64(len(data)) > max {
		return nil, "", fmt.Errorf("object too large")
	}
	contentType, err := os.ReadFile(s.file(key) + ".type")
	return data, string(contentType), err
}
func (s fileArtifactStore) Delete(_ context.Context, key string) error {
	if err := os.Remove(s.file(key)); err != nil && !os.IsNotExist(err) {
		return err
	}
	return nil
}
func (s fileArtifactStore) DeleteMany(ctx context.Context, keys []string) error {
	for _, key := range keys {
		if err := s.Delete(ctx, key); err != nil {
			return err
		}
	}
	return nil
}

type processWorker struct {
	python, script, root, apiURL string
	lastError                    error
}

func (w *processWorker) SupportsStructured(context.Context) bool { return true }
func (w *processWorker) DispatchJob(ctx context.Context, p jobs.DispatchPayload) error {
	raw, err := json.Marshal(p)
	if err != nil {
		return err
	}
	cmd := exec.CommandContext(ctx, w.python, w.script)
	cmd.Stdin = bytes.NewReader(raw)
	cmd.Env = append(os.Environ(), "HYBRID_E2E_STORE="+w.root, "HYBRID_E2E_API="+w.apiURL, "HYBRID_E2E_KEY="+IntegrationWorkerAPIKey)
	output, err := cmd.CombinedOutput()
	if err != nil {
		w.lastError = fmt.Errorf("worker process: %w: %s", err, output)
		return w.lastError
	}
	return nil
}

// Opt in with HYBRID_E2E_PYTHON pointing to a worker environment with dependencies.
func TestHybridGoAndPythonProcesses(t *testing.T) {
	python := os.Getenv("HYBRID_E2E_PYTHON")
	if python == "" {
		t.Skip("HYBRID_E2E_PYTHON not configured")
	}
	env := newTestEnv(t, nil)
	root := t.TempDir()
	store := fileArtifactStore{root: root}
	script, err := filepath.Abs("../../worker/tests/hybrid_e2e_worker.py")
	require.NoError(t, err)
	worker := &processWorker{python: python, script: script, root: root}
	cfg := &config.Config{JWTSecret: testJWTSecret, JWTRefreshSecret: testJWTRefreshSecret, WorkerAPIKey: IntegrationWorkerAPIKey, StructuredPostsEnabled: true}
	server := httptest.NewServer(buildEcho(env.DB, cfg, worker, store))
	t.Cleanup(server.Close)
	env.APIURL = server.URL
	worker.apiURL = server.URL
	token, uid := registerAndLogin(t, env)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", uid) })
	env.putTestProfile(t, token)
	request := func(method, path string, body []byte) *http.Response {
		t.Helper()
		req, err := http.NewRequest(method, server.URL+path, bytes.NewReader(body))
		require.NoError(t, err)
		req.Header.Set("Authorization", "Bearer "+token)
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("X-Post-Client-Version", "1")
		res, err := env.HTTPClient.Do(req)
		require.NoError(t, err)
		return res
	}
	response := request(http.MethodPost, "/chats", []byte(`{"postType":"single"}`))
	require.Equal(t, http.StatusCreated, response.StatusCode)
	var ch struct {
		ID uuid.UUID `json:"id"`
	}
	require.NoError(t, json.NewDecoder(response.Body).Decode(&ch))
	response.Body.Close()
	path := "/chats/" + ch.ID.String()
	response = request(http.MethodPost, path+"/messages", []byte(`{"content":"crie","mode":"create"}`))
	require.NoError(t, worker.lastError)
	require.Equal(t, http.StatusAccepted, response.StatusCode)
	response.Body.Close()
	var first db.PostVersion
	require.NoError(t, env.DB.Where("chat_id = ?", ch.ID).First(&first).Error)
	before, err := store.GetObject(context.Background(), first.DocumentS3Key)
	require.NoError(t, err)
	require.Contains(t, string(before), "Original")
	payload, err := json.Marshal(map[string]string{"content": "edite", "mode": "edit", "baseVersionId": first.ID.String()})
	require.NoError(t, err)
	response = request(http.MethodPost, path+"/messages", payload)
	require.NoError(t, worker.lastError)
	require.Equal(t, http.StatusAccepted, response.StatusCode)
	response.Body.Close()
	var versions []db.PostVersion
	require.NoError(t, env.DB.Where("chat_id = ?", ch.ID).Find(&versions).Error)
	require.Len(t, versions, 2)
	var latest db.PostVersion
	require.NoError(t, env.DB.Where("chat_id = ? AND parent_version_id = ?", ch.ID, first.ID).First(&latest).Error)
	after, err := store.GetObject(context.Background(), latest.DocumentS3Key)
	require.NoError(t, err)
	require.Contains(t, string(after), "Editado")
	original, err := store.GetObject(context.Background(), first.DocumentS3Key)
	require.NoError(t, err)
	require.Equal(t, before, original)
}

// Exercise the real worker HTTP route and background callback with simulated external dependencies.
func TestHybridRealWorkerHTTP(t *testing.T) {
	python := os.Getenv("HYBRID_E2E_PYTHON")
	if python == "" {
		t.Skip("HYBRID_E2E_PYTHON not configured")
	}
	env := newTestEnv(t, nil)
	root := t.TempDir()
	store := fileArtifactStore{root: root}
	script, err := filepath.Abs("../../worker/tests/hybrid_e2e_worker.py")
	require.NoError(t, err)
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	require.NoError(t, err)
	workerAddress := listener.Addr().String()
	require.NoError(t, listener.Close())
	worker := jobs.NewHTTPWorkerClient("http://"+workerAddress, IntegrationWorkerAPIKey)
	cfg := &config.Config{JWTSecret: testJWTSecret, JWTRefreshSecret: testJWTRefreshSecret, WorkerAPIKey: IntegrationWorkerAPIKey, StructuredPostsEnabled: true}
	api := httptest.NewServer(buildEcho(env.DB, cfg, worker, store))
	t.Cleanup(api.Close)
	env.APIURL = api.URL
	_, port, err := net.SplitHostPort(workerAddress)
	require.NoError(t, err)
	cmd := exec.Command(python, script)
	cmd.Env = append(os.Environ(), "HYBRID_E2E_STORE="+root, "HYBRID_E2E_API="+api.URL, "HYBRID_E2E_KEY="+IntegrationWorkerAPIKey, "HYBRID_E2E_PORT="+port)
	var output bytes.Buffer
	cmd.Stdout = &output
	cmd.Stderr = &output
	require.NoError(t, cmd.Start())
	t.Cleanup(func() { _ = cmd.Process.Kill(); _ = cmd.Wait() })
	require.Eventually(t, func() bool { return worker.SupportsStructured(context.Background()) }, 15*time.Second, 100*time.Millisecond, "worker did not become ready")
	token, uid := registerAndLogin(t, env)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", uid) })
	env.putTestProfile(t, token)
	request := func(method, path string, body []byte) *http.Response {
		t.Helper()
		req, err := http.NewRequest(method, api.URL+path, bytes.NewReader(body))
		require.NoError(t, err)
		req.Header.Set("Authorization", "Bearer "+token)
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("X-Post-Client-Version", "1")
		res, err := env.HTTPClient.Do(req)
		require.NoError(t, err)
		return res
	}
	response := request(http.MethodPost, "/chats", []byte(`{"postType":"single"}`))
	require.Equal(t, http.StatusCreated, response.StatusCode)
	var ch struct {
		ID uuid.UUID `json:"id"`
	}
	require.NoError(t, json.NewDecoder(response.Body).Decode(&ch))
	response.Body.Close()
	path := "/chats/" + ch.ID.String()
	response = request(http.MethodPost, path+"/messages", []byte(`{"content":"crie","mode":"create"}`))
	require.Equal(t, http.StatusAccepted, response.StatusCode)
	var job struct {
		JobID uuid.UUID `json:"jobId"`
	}
	require.NoError(t, json.NewDecoder(response.Body).Decode(&job))
	response.Body.Close()
	poll := func(id uuid.UUID) string {
		t.Helper()
		deadline := time.Now().Add(30 * time.Second)
		for time.Now().Before(deadline) {
			status, _ := getJobStatus(t, env, token, ch.ID, id)
			if status == "done" || status == "failed" {
				return status
			}
			time.Sleep(time.Second)
		}
		t.Fatal("job did not reach a terminal state")
		return ""
	}
	status := poll(job.JobID)
	require.Equal(t, "done", status)
	var first db.PostVersion
	require.NoError(t, env.DB.Where("job_id = ?", job.JobID).First(&first).Error)
	payload, err := json.Marshal(map[string]string{"content": "edite", "mode": "edit", "baseVersionId": first.ID.String()})
	require.NoError(t, err)
	response = request(http.MethodPost, path+"/messages", payload)
	require.Equal(t, http.StatusAccepted, response.StatusCode)
	require.NoError(t, json.NewDecoder(response.Body).Decode(&job))
	response.Body.Close()
	status = poll(job.JobID)
	require.Equal(t, "done", status)
	var second db.PostVersion
	require.NoError(t, env.DB.Where("job_id = ?", job.JobID).First(&second).Error)
	require.Equal(t, first.ID, *second.ParentVersionID)
	before, err := store.GetObject(context.Background(), first.DocumentS3Key)
	require.NoError(t, err)
	require.Contains(t, string(before), "Original")
	after, err := store.GetObject(context.Background(), second.DocumentS3Key)
	require.NoError(t, err)
	require.Contains(t, string(after), "Editado")
}
