package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"content-creator-agent/internal/auth"
	"content-creator-agent/internal/chat"
	"content-creator-agent/internal/config"
	appcron "content-creator-agent/internal/cron"
	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	appmw "content-creator-agent/internal/middleware"
	"content-creator-agent/internal/profile"
	"content-creator-agent/internal/storage"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

const maxRequestBodySize = "22M"

func main() {
	cfg := config.Load()
	if cfg.JWTSecret == "" || cfg.JWTRefreshSecret == "" {
		log.Fatal("JWT_SECRET and JWT_REFRESH_SECRET must be set")
	}

	gdb := db.Connect()
	if err := db.RunMigrations(os.Getenv("DATABASE_URL")); err != nil {
		log.Fatalf("migrations: %v", err)
	}

	repo := auth.NewRepository(gdb)
	cookieSecure := os.Getenv("COOKIE_SECURE") != "false"
	svc := auth.NewService(repo, cfg.JWTSecret, cfg.JWTRefreshSecret, cookieSecure)
	h := auth.NewHandler(svc)

	stor, err := storage.NewS3Service(cfg.AWSRegion, cfg.S3Bucket, cfg.AWSAccessKeyID, cfg.AWSSecretAccessKey, storage.S3Options{ForcePathStyle: cfg.S3ForcePathStyle, PublicEndpoint: cfg.S3PublicEndpoint})
	if err != nil {
		log.Fatalf("storage: %v", err)
	}
	chatRepo := chat.NewRepository(gdb)
	jobsRepo := jobs.NewRepository(gdb)
	profileRepo := profile.NewRepository(gdb)
	refRepo := profile.NewReferencesRepository(gdb)
	profileSvc := profile.NewService(profileRepo, refRepo, stor, cfg.ProfileRefMaxCount, cfg.ProfileRefMaxBytes)
	profileH := profile.NewHandler(profileSvc)
	wURL := strings.TrimSpace(cfg.WorkerURL)
	wKey := strings.TrimSpace(cfg.WorkerAPIKey)
	if wURL != "" && wKey == "" {
		log.Fatal("WORKER_API_KEY must be set when WORKER_URL is configured")
	}
	if wKey != "" && wURL == "" {
		log.Fatal("WORKER_URL must be set when WORKER_API_KEY is configured")
	}
	var worker jobs.WorkerClient
	var structuredReady func(context.Context) bool
	var referencePolicyReady func(context.Context) bool
	var visualV2Ready func(context.Context, int) bool
	var stockImagesReady func(context.Context, int) bool
	if wURL != "" {
		pool, err := jobs.NewStructuredWorkerPool(jobs.NewHTTPWorkerClient(wURL, wKey), cfg.StructuredWorkerURLs, wKey)
		if err != nil {
			log.Fatalf("invalid structured worker configuration: %v", err)
		}
		worker = pool
		structuredReady = pool.SupportsStructured
		referencePolicyReady = pool.SupportsReferencePolicy
		visualV2Ready = pool.SupportsStructuredV2
		stockImagesReady = pool.SupportsStructuredV3
	}
	chatSvc := chat.NewService(chatRepo, jobsRepo, stor, profileRepo, profileSvc, worker)
	chatSvc.ConfigureStructured(cfg.StructuredPostsEnabled, structuredReady)
	chatSvc.ConfigureReferencePolicy(referencePolicyReady)
	chatSvc.ConfigureVisualV2(cfg.StructuredVisualV2Enabled, cfg.StructuredVisualV2MutationsDisabled, visualV2Ready)
	chatSvc.ConfigureStockImages(cfg.StructuredStockImagesEnabled, stockImagesReady)
	ch := chat.NewHandler(chatSvc)

	jobsH := jobs.NewHandler(&cfg, gdb, stor)

	sched := appcron.New()
	if strings.TrimSpace(cfg.StuckJobCron) != "" {
		maxAge := time.Duration(cfg.StuckJobProcessingMinutes) * time.Minute
		if err := sched.RegisterSafe(cfg.StuckJobCron, "stuck-job-cleanup", func() {
			n, err := jobs.RunStuckJobCleanup(context.Background(), jobsRepo, maxAge)
			if err != nil {
				log.Printf("[metrics] event=stuck_job_cleanup outcome=failed")
				log.Printf("[jobs] stuck cleanup error: %v", err)
				return
			}
			log.Printf("[metrics] event=stuck_job_cleanup outcome=done jobs=%d threshold_minutes=%d", n, cfg.StuckJobProcessingMinutes)
		}); err != nil {
			log.Fatalf("cron stuck jobs: %v", err)
		}
		log.Printf("[jobs] stuck-job cleanup registered expr=%q threshold=%dm (UTC)", cfg.StuckJobCron, cfg.StuckJobProcessingMinutes)
	}
	if cfg.ArtifactReconcileEnabled {
		if err := sched.RegisterSafe(cfg.ArtifactReconcileCron, "artifact-reconcile", func() {
			ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
			defer cancel()
			cutoff := time.Now().UTC().Add(-time.Duration(cfg.ArtifactReconcileGraceHours) * time.Hour)
			if err := jobs.ReconcileArtifacts(ctx, gdb, stor, cutoff); err != nil {
				log.Printf("[jobs] artifact reconciliation failed")
				return
			}
			log.Printf("[jobs] artifact reconciliation completed")
		}); err != nil {
			log.Fatalf("cron artifact reconciliation: %v", err)
		}
	}
	if err := sched.RegisterSafe("0 3 * * *", "token-purge", func() {
		n, err := repo.DeleteExpiredRefreshTokens(context.Background())
		if err != nil {
			log.Printf("[auth] token purge error: %v", err)
			return
		}
		if n > 0 {
			log.Printf("[auth] token purge: deleted %d expired refresh token(s)", n)
		}
	}); err != nil {
		log.Fatalf("cron token purge: %v", err)
	}
	sched.Start()

	e := echo.New()
	e.HideBanner = true
	e.IPExtractor = echo.ExtractIPFromXFFHeader(echo.TrustPrivateNet(true))
	e.Use(middleware.Recover())
	e.Use(middleware.Logger())
	e.Use(middleware.BodyLimit(maxRequestBodySize))
	e.Use(appmw.SecurityHeaders(cookieSecure))
	e.Use(appmw.CORS(cfg.CORSAllowedOrigins))

	e.GET("/health", func(c echo.Context) error {
		return c.JSON(http.StatusOK, map[string]string{"status": "ok"})
	})

	authGroup := e.Group("/auth")
	authGroup.Use(appmw.AuthByIP())
	authGroup.POST("/register", h.Register)
	authGroup.POST("/login", h.Login)
	authGroup.POST("/logout", h.Logout)
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
	protected.GET("/chats/:id/contents/:contentId/download", ch.DownloadContentZip)
	protected.GET("/chats/:id/files", ch.ListFiles)
	protected.GET("/chats/:id/files/:fileId", ch.GetFile)
	protected.GET("/setup/status", ch.SetupStatus)
	protected.GET("/profile", profileH.Get)
	protected.PUT("/profile", profileH.Save)
	protected.DELETE("/profile/references/:id", profileH.DeleteReference)

	chatLLM := protected.Group("/chats")
	chatLLM.Use(appmw.LLMByUser())
	chatLLM.POST("/:id/messages", ch.PostMessage)
	chatLLM.GET("/:id/jobs/:jobId/status", ch.GetJobStatus)

	llm := protected.Group("/api/llm")
	llm.Use(appmw.LLMByUser())
	llm.GET("/ready", func(c echo.Context) error {
		return c.JSON(http.StatusOK, map[string]string{"status": "ok"})
	})

	// Internal server on a separate port — never exposed to the host in docker-compose.
	internalE := echo.New()
	internalE.HideBanner = true
	internalE.Use(middleware.Logger())
	internalE.POST("/internal/jobs/:id/complete", jobsH.Complete)
	internalE.POST("/internal/jobs/:id/progress", jobsH.Progress)

	addr := ":" + cfg.Port
	go func() {
		if err := e.Start(addr); err != nil && err != http.ErrServerClosed {
			log.Fatal(err)
		}
	}()
	go func() {
		if err := internalE.Start(":8081"); err != nil && err != http.ErrServerClosed {
			log.Fatal(err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt, syscall.SIGTERM)
	<-quit

	log.Print("[cron] stopping scheduler")
	sched.Stop()
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := e.Shutdown(shutdownCtx); err != nil {
		log.Fatalf("shutdown: %v", err)
	}
	if err := internalE.Shutdown(shutdownCtx); err != nil {
		log.Fatalf("internal shutdown: %v", err)
	}
}
