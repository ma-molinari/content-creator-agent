//go:build integration

package integration

import (
	"bytes"
	"context"
	"embed"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	"content-creator-agent/internal/auth"
	"content-creator-agent/internal/chat"
	"content-creator-agent/internal/config"
	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	appmw "content-creator-agent/internal/middleware"
	"content-creator-agent/internal/storage"

	"github.com/google/uuid"
	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
	"github.com/stretchr/testify/require"
	"gorm.io/gorm"
)

//go:embed testdata/AUDIT.md testdata/BRAND.md
var profileTestdata embed.FS

const (
	testJWTSecret        = "integration-test-jwt-access-secret-min-32"
	testJWTRefreshSecret = "integration-test-jwt-refresh-secret-min-32"
	// IntegrationWorkerAPIKey is the shared key used by newTestEnv and mock worker callbacks.
	IntegrationWorkerAPIKey = "integration-worker-api-key"
)

type mockStorage struct{}

func (mockStorage) Upload(_ context.Context, _ string, _ []byte) error { return nil }

func (mockStorage) GetSignedURL(_ context.Context, key string, _ time.Duration) (string, error) {
	return "https://integration.test/presigned/" + key, nil
}

func (mockStorage) GetObject(_ context.Context, _ string) ([]byte, error) { return []byte{0xff, 0xd8}, nil }

func (mockStorage) Delete(_ context.Context, _ string) error { return nil }

func (mockStorage) DeleteMany(_ context.Context, _ []string) error { return nil }

var _ storage.StorageService = mockStorage{}

// testEnv holds shared integration test resources.
type testEnv struct {
	T           *testing.T
	APIURL      string
	DB          *gorm.DB
	DSN         string
	ProfileRoot string
	WorkerKey   string
	HTTPClient  *http.Client
}

func (e *testEnv) writeProfileFiles(userID uuid.UUID) {
	t := e.T
	dir := filepath.Join(e.ProfileRoot, "instagram-audits", userID.String())
	require.NoError(t, os.MkdirAll(dir, 0o755))
	audit, err := profileTestdata.ReadFile("testdata/AUDIT.md")
	require.NoError(t, err)
	brand, err := profileTestdata.ReadFile("testdata/BRAND.md")
	require.NoError(t, err)
	require.NoError(t, os.WriteFile(filepath.Join(dir, "AUDIT.md"), audit, 0o644))
	require.NoError(t, os.WriteFile(filepath.Join(dir, "BRAND.md"), brand, 0o644))
}

func buildEcho(gdb *gorm.DB, cfg *config.Config, profileRoot string, worker jobs.WorkerClient, stor storage.StorageService) *echo.Echo {
	repo := auth.NewRepository(gdb)
	svc := auth.NewService(repo, cfg.JWTSecret, cfg.JWTRefreshSecret, false)
	h := auth.NewHandler(svc)

	chatRepo := chat.NewRepository(gdb)
	jobsRepo := jobs.NewRepository(gdb)
	chatSvc := chat.NewService(chatRepo, jobsRepo, stor, profileRoot, worker)
	ch := chat.NewHandler(chatSvc)

	jobsH := jobs.NewHandler(cfg, jobsRepo, gdb, stor)

	e := echo.New()
	e.HideBanner = true
	e.Use(middleware.Recover())
	e.Use(appmw.SecurityHeaders())
	e.Use(appmw.CORS(cfg.CORSAllowedOrigins))

	e.GET("/health", func(c echo.Context) error {
		return c.JSON(http.StatusOK, map[string]string{"status": "ok"})
	})

	authGroup := e.Group("/auth")
	authGroup.Use(appmw.AuthByIP())
	authGroup.POST("/register", h.Register)
	authGroup.POST("/login", h.Login)
	authGroup.POST("/refresh", h.Refresh)
	authGroup.POST("/recover-password", h.RecoverPassword)

	protected := e.Group("")
	protected.Use(appmw.JWT(cfg.JWTSecret))
	protected.GET("/me", func(c echo.Context) error {
		uid := appmw.UserID(c)
		return c.JSON(http.StatusOK, map[string]string{"userId": uid.String()})
	})

	protected.GET("/chats", ch.ListChats)
	protected.POST("/chats", ch.CreateChat)
	protected.GET("/chats/:id", ch.GetChat)
	protected.DELETE("/chats/:id", ch.DeleteChat)
	protected.GET("/chats/:id/files/download", ch.DownloadZip)
	protected.GET("/chats/:id/files", ch.ListFiles)
	protected.GET("/chats/:id/files/:fileId", ch.GetFile)
	protected.GET("/setup/status", ch.SetupStatus)

	chatLLM := protected.Group("/chats")
	chatLLM.Use(appmw.LLMByUser())
	chatLLM.POST("/:id/messages", ch.PostMessage)
	chatLLM.GET("/:id/jobs/:jobId/status", ch.GetJobStatus)

	llm := protected.Group("/api/llm")
	llm.Use(appmw.LLMByUser())
	llm.GET("/ready", func(c echo.Context) error {
		return c.JSON(http.StatusOK, map[string]string{"status": "ok"})
	})

	internal := e.Group("/internal")
	internal.POST("/jobs/:id/complete", jobsH.Complete)

	return e
}

// newWorkerServer mounts POST /jobs and forwards to h after validating the API key.
// apiBase must point to the Go API base URL (set after httptest.NewServer for the API).
func newWorkerServer(t *testing.T, apiKey string, apiBase *string, h func(w http.ResponseWriter, r *http.Request, apiBase string)) *httptest.Server {
	t.Helper()
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/jobs" || r.Method != http.MethodPost {
			http.NotFound(w, r)
			return
		}
		if r.Header.Get("X-Worker-API-Key") != apiKey {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		base := ""
		if apiBase != nil {
			base = *apiBase
		}
		h(w, r, base)
	}))
}

func newTestEnv(t *testing.T, workerHandler func(w http.ResponseWriter, r *http.Request, apiBase string)) *testEnv {
	t.Helper()
	dsn := os.Getenv("INTEGRATION_DATABASE_URL")
	if dsn == "" {
		t.Skip("INTEGRATION_DATABASE_URL not set; skip integration tests")
	}

	gdb, err := db.ConnectWithURL(dsn)
	require.NoError(t, err)
	t.Cleanup(func() {
		sqlDB, err := gdb.DB()
		if err == nil {
			_ = sqlDB.Close()
		}
	})

	require.NoError(t, db.RunMigrations(dsn))

	profileRoot := t.TempDir()
	workerKey := IntegrationWorkerAPIKey

	apiBasePtr := new(string)
	workerSrv := newWorkerServer(t, workerKey, apiBasePtr, workerHandler)
	t.Cleanup(workerSrv.Close)

	cfg := &config.Config{
		JWTSecret:        testJWTSecret,
		JWTRefreshSecret: testJWTRefreshSecret,
		WorkerAPIKey:     workerKey,
	}
	workerClient := jobs.NewHTTPWorkerClient(workerSrv.URL, workerKey)
	e := buildEcho(gdb, cfg, profileRoot, workerClient, mockStorage{})
	apiSrv := httptest.NewServer(e)
	t.Cleanup(apiSrv.Close)

	*apiBasePtr = apiSrv.URL

	return &testEnv{
		T:           t,
		APIURL:      apiSrv.URL,
		DB:          gdb,
		DSN:         dsn,
		ProfileRoot: profileRoot,
		WorkerKey:   workerKey,
		HTTPClient:  &http.Client{Timeout: 30 * time.Second},
	}
}

func registerAndLogin(t *testing.T, env *testEnv) (accessToken string, userID uuid.UUID) {
	t.Helper()
	email := uuid.New().String() + "@integration.test"
	password := "password123"

	regBody := map[string]string{"email": email, "password": password}
	regJSON, _ := json.Marshal(regBody)
	req, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/register", bytes.NewReader(regJSON))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusCreated, res.StatusCode)

	loginBody := map[string]string{"email": email, "password": password}
	loginJSON, _ := json.Marshal(loginBody)
	req2, err := http.NewRequest(http.MethodPost, env.APIURL+"/auth/login", bytes.NewReader(loginJSON))
	require.NoError(t, err)
	req2.Header.Set("Content-Type", "application/json")
	res2, err := env.HTTPClient.Do(req2)
	require.NoError(t, err)
	defer res2.Body.Close()
	require.Equal(t, http.StatusOK, res2.StatusCode)
	var loginResp struct {
		AccessToken string `json:"accessToken"`
	}
	require.NoError(t, json.NewDecoder(res2.Body).Decode(&loginResp))
	require.NotEmpty(t, loginResp.AccessToken)

	req3, err := http.NewRequest(http.MethodGet, env.APIURL+"/me", nil)
	require.NoError(t, err)
	req3.Header.Set("Authorization", "Bearer "+loginResp.AccessToken)
	res3, err := env.HTTPClient.Do(req3)
	require.NoError(t, err)
	defer res3.Body.Close()
	require.Equal(t, http.StatusOK, res3.StatusCode)
	var me struct {
		UserID string `json:"userId"`
	}
	require.NoError(t, json.NewDecoder(res3.Body).Decode(&me))
	uid, err := uuid.Parse(me.UserID)
	require.NoError(t, err)

	return loginResp.AccessToken, uid
}

func createChat(t *testing.T, env *testEnv, token string) uuid.UUID {
	t.Helper()
	body := map[string]string{"postType": "single"}
	b, _ := json.Marshal(body)
	req, err := http.NewRequest(http.MethodPost, env.APIURL+"/chats", bytes.NewReader(b))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+token)
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusCreated, res.StatusCode)
	var out struct {
		ID uuid.UUID `json:"id"`
	}
	require.NoError(t, json.NewDecoder(res.Body).Decode(&out))
	return out.ID
}

func postMessage(t *testing.T, env *testEnv, token string, chatID uuid.UUID, content string) uuid.UUID {
	t.Helper()
	body := map[string]string{"content": content}
	b, _ := json.Marshal(body)
	req, err := http.NewRequest(http.MethodPost, env.APIURL+"/chats/"+chatID.String()+"/messages", bytes.NewReader(b))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+token)
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusAccepted, res.StatusCode)
	var out struct {
		JobID uuid.UUID `json:"jobId"`
	}
	require.NoError(t, json.NewDecoder(res.Body).Decode(&out))
	return out.JobID
}

func getJobStatus(t *testing.T, env *testEnv, token string, chatID, jobID uuid.UUID) (status string, errMsg *string) {
	t.Helper()
	req, err := http.NewRequest(http.MethodGet, env.APIURL+"/chats/"+chatID.String()+"/jobs/"+jobID.String()+"/status", nil)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+token)
	res, err := env.HTTPClient.Do(req)
	require.NoError(t, err)
	defer res.Body.Close()
	require.Equal(t, http.StatusOK, res.StatusCode)
	var out struct {
		Status string  `json:"status"`
		Error  *string `json:"error"`
	}
	require.NoError(t, json.NewDecoder(res.Body).Decode(&out))
	return out.Status, out.Error
}

func pollJobDone(t *testing.T, env *testEnv, token string, chatID, jobID uuid.UUID, timeout time.Duration) (status string, errMsg *string) {
	t.Helper()
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		s, emsg := getJobStatus(t, env, token, chatID, jobID)
		if s == "done" || s == "failed" {
			return s, emsg
		}
		time.Sleep(50 * time.Millisecond)
	}
	t.Fatalf("timeout waiting for job %s", jobID)
	return "", nil
}

func lastJobIDForChat(t *testing.T, env *testEnv, chatID uuid.UUID) uuid.UUID {
	t.Helper()
	var j db.Job
	err := env.DB.WithContext(context.Background()).
		Where("chat_id = ?", chatID).
		Order("created_at DESC").
		First(&j).Error
	require.NoError(t, err)
	require.NotEqual(t, uuid.Nil, j.ID)
	return j.ID
}
