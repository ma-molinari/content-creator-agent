package main

import (
	"log"
	"net/http"
	"os"

	"content-creator-agent/internal/auth"
	"content-creator-agent/internal/chat"
	"content-creator-agent/internal/config"
	"content-creator-agent/internal/db"
	appmw "content-creator-agent/internal/middleware"
	"content-creator-agent/internal/storage"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

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

	stor, err := storage.NewS3Service(cfg.AWSRegion, cfg.S3Bucket, cfg.AWSAccessKeyID, cfg.AWSSecretAccessKey)
	if err != nil {
		log.Fatalf("storage: %v", err)
	}
	chatRepo := chat.NewRepository(gdb)
	chatSvc := chat.NewService(chatRepo, stor)
	ch := chat.NewHandler(chatSvc)
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
	llm := protected.Group("/api/llm")
	llm.Use(appmw.LLMByUser())
	llm.GET("/ready", func(c echo.Context) error {
		return c.JSON(http.StatusOK, map[string]string{"status": "ok"})
	})

	addr := ":" + cfg.Port
	if err := e.Start(addr); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
}
