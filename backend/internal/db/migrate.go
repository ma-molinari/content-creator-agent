package db

import (
	"embed"
	"errors"
	"fmt"

	"github.com/golang-migrate/migrate/v4"
	"github.com/golang-migrate/migrate/v4/database/postgres"
	"github.com/golang-migrate/migrate/v4/source/iofs"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/stdlib"
)

//go:embed migrations/*.sql
var migrationFiles embed.FS

// RunMigrations applies embedded SQL migrations (up).
func RunMigrations(databaseURL string) error {
	if databaseURL == "" {
		return fmt.Errorf("database URL is empty")
	}
	d, err := iofs.New(migrationFiles, "migrations")
	if err != nil {
		return fmt.Errorf("migration fs: %w", err)
	}
	cfg, err := pgx.ParseConfig(databaseURL)
	if err != nil {
		return fmt.Errorf("parse database URL: %w", err)
	}
	sqlDB := stdlib.OpenDB(*cfg)
	driver, err := postgres.WithInstance(sqlDB, &postgres.Config{})
	if err != nil {
		return fmt.Errorf("postgres migrate driver: %w", err)
	}
	m, err := migrate.NewWithInstance("iofs", d, "postgres", driver)
	if err != nil {
		return fmt.Errorf("migrate: %w", err)
	}
	defer m.Close()
	if err := m.Up(); err != nil && !errors.Is(err, migrate.ErrNoChange) {
		return err
	}
	return nil
}

// RollbackAllMigrations runs every down migration until none remain (for tests).
func RollbackAllMigrations(databaseURL string) error {
	if databaseURL == "" {
		return fmt.Errorf("database URL is empty")
	}
	d, err := iofs.New(migrationFiles, "migrations")
	if err != nil {
		return fmt.Errorf("migration fs: %w", err)
	}
	cfg, err := pgx.ParseConfig(databaseURL)
	if err != nil {
		return fmt.Errorf("parse database URL: %w", err)
	}
	sqlDB := stdlib.OpenDB(*cfg)
	driver, err := postgres.WithInstance(sqlDB, &postgres.Config{})
	if err != nil {
		return fmt.Errorf("postgres migrate driver: %w", err)
	}
	m, err := migrate.NewWithInstance("iofs", d, "postgres", driver)
	if err != nil {
		return fmt.Errorf("migrate: %w", err)
	}
	defer m.Close()
	for {
		if err := m.Steps(-1); err != nil {
			if errors.Is(err, migrate.ErrNoChange) {
				return nil
			}
			return err
		}
	}
}
