package db

import (
	"os"
	"testing"
)

func TestConnectPanicsWithoutDatabaseURL(t *testing.T) {
	t.Setenv("DATABASE_URL", "")
	defer func() {
		r := recover()
		if r == nil {
			t.Fatal("expected panic when DATABASE_URL is empty")
		}
	}()
	Connect()
}

func TestConnectWithURLRequiresNonEmpty(t *testing.T) {
	_, err := ConnectWithURL("")
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestMigrationsApplyAndRollback(t *testing.T) {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		t.Skip("DATABASE_URL not set; skipping integration test")
	}
	if err := RunMigrations(dsn); err != nil {
		t.Fatalf("up: %v", err)
	}
	if err := RollbackAllMigrations(dsn); err != nil {
		t.Fatalf("down: %v", err)
	}
	if err := RunMigrations(dsn); err != nil {
		t.Fatalf("up again: %v", err)
	}
}
