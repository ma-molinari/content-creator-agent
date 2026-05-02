package chat

import (
	"context"
	"fmt"
	"testing"
	"time"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

type mockStorage struct {
	deleteManyCalls int
	signedURLCalls  int
}

func (m *mockStorage) Upload(context.Context, string, []byte) error { return nil }

func (m *mockStorage) GetSignedURL(context.Context, string, time.Duration) (string, error) {
	m.signedURLCalls++
	return fmt.Sprintf("https://example.com/signed-%d", m.signedURLCalls), nil
}

func (m *mockStorage) GetObject(context.Context, string) ([]byte, error) {
	return []byte{0xff, 0xd8}, nil
}

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
		`CREATE TABLE chat_content_resume (
			id TEXT PRIMARY KEY,
			chat_id TEXT NOT NULL UNIQUE,
			summary TEXT,
			last_content_at DATETIME,
			summarized_at DATETIME,
			created_at DATETIME,
			updated_at DATETIME,
			FOREIGN KEY (chat_id) REFERENCES chats(id)
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
	svc := NewService(repo, jobsRepo, store, nil, nil, nil)
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
	var n int64
	if err := gdb.WithContext(ctx).Model(&db.Chat{}).Where("user_id = ?", u.ID).Count(&n).Error; err != nil {
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
	svc := NewService(repo, jobsRepo, store, nil, nil, nil)
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
	var nAfter int64
	if err := gdb.WithContext(ctx).Model(&db.Chat{}).Where("user_id = ?", u.ID).Count(&nAfter).Error; err != nil {
		t.Fatal(err)
	}
	if nAfter != 5 {
		t.Fatalf("want 5 chats after eviction, got %d", nAfter)
	}
}

func TestChatLimit_oneNoEviction(t *testing.T) {
	gdb, u := testDBWithUser(t)
	store := &mockStorage{}
	svc := NewService(NewRepository(gdb), jobs.NewRepository(gdb), store, nil, nil, nil)
	ctx := context.Background()
	if _, err := svc.CreateChat(ctx, u.ID, "carousel"); err != nil {
		t.Fatal(err)
	}
	if store.deleteManyCalls != 0 {
		t.Fatalf("unexpected eviction")
	}
}

func TestGetChat_refreshesPresignedURLsPerImage(t *testing.T) {
	gdb, u := testDBWithUser(t)
	store := &mockStorage{}
	repo := NewRepository(gdb)
	svc := NewService(repo, jobs.NewRepository(gdb), store, nil, nil, nil)
	ctx := context.Background()

	c, err := svc.CreateChat(ctx, u.ID, "single")
	require.NoError(t, err)

	ccID := uuid.New()
	require.NoError(t, gdb.Create(&db.ChatContent{
		ID:        ccID,
		ChatID:    c.ID,
		Role:      db.ChatContentRoleAssistant,
		Content:   "hello",
		CreatedAt: time.Now().UTC(),
		UpdatedAt: time.Now().UTC(),
	}).Error)
	require.NoError(t, gdb.Create(&db.ChatContentImage{
		ID:            uuid.New(),
		ChatContentID: ccID,
		S3Key:         "slides/job/slide1.jpg",
		URL:           "https://stale.example/old",
		SlideNumber:   1,
		CreatedAt:     time.Now().UTC(),
		UpdatedAt:     time.Now().UTC(),
	}).Error)

	chat, err := svc.GetChat(ctx, u.ID, c.ID)
	require.NoError(t, err)
	require.Len(t, chat.Contents, 1)
	require.Len(t, chat.Contents[0].Images, 1)
	require.Equal(t, "https://example.com/signed-1", chat.Contents[0].Images[0].URL)
	require.Equal(t, 1, store.signedURLCalls)
}
