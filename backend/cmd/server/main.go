package main

import (
	"log"
	"net/http"
	"os"

	"content-creator-agent/internal/config"
	"content-creator-agent/internal/db"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

func main() {
	cfg := config.Load()
	_ = cfg
	gdb := db.Connect()
	if err := db.RunMigrations(os.Getenv("DATABASE_URL")); err != nil {
		log.Fatalf("migrations: %v", err)
	}
	_ = gdb

	e := echo.New()
	e.HideBanner = true
	e.Use(middleware.Recover())
	e.GET("/health", func(c echo.Context) error {
		return c.JSON(http.StatusOK, map[string]string{"status": "ok"})
	})
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	if err := e.Start(":" + port); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
}
