package chat

import (
	"context"
	"testing"
	"time"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"

	"github.com/google/uuid"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

type mockStorage struct {
	deleteManyCalls int
}

func (m *mockStorage) Upload(context.Context, string, []byte) error { return nil }

func (m *mockStorage) GetSignedURL(context.Context, string, time.Duration) (string, error) {
	return "https://example.com/signed", nil
}

func (m *mockStorage) GetObject(context.Context, string) ([]byte, error) { return []byte{0xff, 0xd8}, nil }

func (m *mockStorage) Delete(context.Context, string) error { return nil }

func (m *mockStorage) DeleteMany(context.Context, []string) error {
	m.deleteManyCalls++
	return nil
}

func testDBWithUser(t *testing.T) (*gorm.DB, *db.User) {
	t.Helper()
	gdb, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatal(err)
	}
	// Minimal SQLite DDL (Postgres-specific defaults from AutoMigrate are not portable).
	stmts := []string{
		`CREATE TABLE users (
			id TEXT PRIMARY KEY,
			email TEXT NOT NULL UNIQUE,
			password_hash TEXT NOT NULL,
			security_key_hash TEXT NOT NULL,
			role TEXT NOT NULL,
			created_at DATETIME,
			updated_at DATETIME
		)`,
		`CREATE TABLE chats (
			id TEXT PRIMARY KEY,
			user_id TEXT NOT NULL,
			post_type TEXT NOT NULL,
			title TEXT,
			created_at DATETIME,
			updated_at DATETIME,
			FOREIGN KEY (user_id) REFERENCES users(id)
		)`,
		`CREATE TABLE chat_content (
			id TEXT PRIMARY KEY,
			chat_id TEXT NOT NULL,
			role TEXT NOT NULL,
			content TEXT NOT NULL,
			created_at DATETIME,
			updated_at DATETIME,
			FOREIGN KEY (chat_id) REFERENCES chats(id)
		)`,
		`CREATE TABLE chat_content_image (
			id TEXT PRIMARY KEY,
			chat_content_id TEXT NOT NULL,
			s3_key TEXT NOT NULL,
			url TEXT NOT NULL,
			slide_number INTEGER NOT NULL,
			created_at DATETIME,
			updated_at DATETIME,
			FOREIGN KEY (chat_content_id) REFERENCES chat_content(id)
		)`,
	}
	for _, q := range stmts {
		if err := gdb.Exec(q).Error; err != nil {
			t.Fatal(err)
		}
	}
	u := &db.User{
		ID:              uuid.New(),
		Email:           "test-" + uuid.NewString() + "@example.com",
		PasswordHash:    "x",
		SecurityKeyHash: "y",
		Role:            db.RoleUser,
	}
	if err := gdb.Create(u).Error; err != nil {
		t.Fatal(err)
	}
	return gdb, u
}

func TestChatLimit_fourThenFifthNoEviction(t *testing.T) {
	gdb, u := testDBWithUser(t)
	repo := NewRepository(gdb)
	jobsRepo := jobs.NewRepository(gdb)
	store := &mockStorage{}
	svc := NewService(repo, jobsRepo, store, "", nil)
	ctx := context.Background()
	for range 4 {
		if _, err := svc.CreateChat(ctx, u.ID, "single"); err != nil {
			t.Fatal(err)
		}
	}
	if store.deleteManyCalls != 0 {
		t.Fatalf("expected no eviction, got %d", store.deleteManyCalls)
	}
	if _, err := svc.CreateChat(ctx, u.ID, "single"); err != nil {
		t.Fatal(err)
	}
	n, err := repo.CountByUser(ctx, u.ID)
	if err != nil {
		t.Fatal(err)
	}
	if n != 5 {
		t.Fatalf("want 5 chats, got %d", n)
	}
	if store.deleteManyCalls != 0 {
		t.Fatalf("expected no S3 delete when going from 4 to 5")
	}
}

func TestChatLimit_sixthEvictsOldest(t *testing.T) {
	gdb, u := testDBWithUser(t)
	repo := NewRepository(gdb)
	jobsRepo := jobs.NewRepository(gdb)
	store := &mockStorage{}
	svc := NewService(repo, jobsRepo, store, "", nil)
	ctx := context.Background()
	var firstID uuid.UUID
	for i := range 5 {
		if i > 0 {
			time.Sleep(5 * time.Millisecond)
		}
		c, err := svc.CreateChat(ctx, u.ID, "single")
		if err != nil {
			t.Fatal(err)
		}
		if i == 0 {
			firstID = c.ID
		}
	}
	if _, err := svc.CreateChat(ctx, u.ID, "single"); err != nil {
		t.Fatal(err)
	}
	if store.deleteManyCalls != 1 {
		t.Fatalf("want 1 DeleteMany (eviction), got %d", store.deleteManyCalls)
	}
	_, err := repo.GetByID(ctx, firstID)
	if err == nil || !ErrRecordNotFound(err) {
		t.Fatal("oldest chat should be removed")
	}
	n, err := repo.CountByUser(ctx, u.ID)
	if err != nil {
		t.Fatal(err)
	}
	if n != 5 {
		t.Fatalf("want 5 chats after eviction, got %d", n)
	}
}

func TestChatLimit_oneNoEviction(t *testing.T) {
	gdb, u := testDBWithUser(t)
	store := &mockStorage{}
	svc := NewService(NewRepository(gdb), jobs.NewRepository(gdb), store, "", nil)
	ctx := context.Background()
	if _, err := svc.CreateChat(ctx, u.ID, "carousel"); err != nil {
		t.Fatal(err)
	}
	if store.deleteManyCalls != 0 {
		t.Fatalf("unexpected eviction")
	}
}
