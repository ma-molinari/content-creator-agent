package main

import (
	"log"
	"net/http"
	"os"

	"content-creator-agent/internal/auth"
	"content-creator-agent/internal/config"
	"content-creator-agent/internal/db"
	appmw "content-creator-agent/internal/middleware"

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

	e := echo.New()
	e.HideBanner = true
	e.Use(middleware.Recover())
	e.GET("/health", func(c echo.Context) error {
		return c.JSON(http.StatusOK, map[string]string{"status": "ok"})
	})

	authGroup := e.Group("/auth")
	authGroup.POST("/register", h.Register)
	authGroup.POST("/login", h.Login)
	authGroup.POST("/refresh", h.Refresh)

	protected := e.Group("")
	protected.Use(appmw.JWT(cfg.JWTSecret))
	protected.GET("/me", func(c echo.Context) error {
		uid := appmw.UserID(c)
		return c.JSON(http.StatusOK, map[string]string{"userId": uid.String()})
	})
	protected.GET("/chats", func(c echo.Context) error {
		return c.JSON(http.StatusOK, []interface{}{})
	})

	addr := ":" + cfg.Port
	if err := e.Start(addr); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
}
