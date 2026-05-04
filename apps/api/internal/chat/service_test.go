package chat

import (
	"context"
	"errors"
	"fmt"
	"testing"
	"time"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"content-creator-agent/internal/profile"
	"content-creator-agent/internal/storage"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

type mockDispatchWorker struct {
	fn func(*jobs.DispatchPayload) error
}

func (m *mockDispatchWorker) DispatchJob(ctx context.Context, p jobs.DispatchPayload) error {
	if m.fn != nil {
		return m.fn(&p)
	}
	return nil
}

type mockStorage struct {
	deleteManyCalls int
	signedURLCalls  int
}

func (m *mockStorage) Upload(context.Context, string, []byte) error { return nil }

func (m *mockStorage) GetSignedURL(context.Context, string, time.Duration) (string, error) {
	m.signedURLCalls++
	return fmt.Sprintf("https://example.com/signed-%d", m.signedURLCalls), nil
}

func (m *mockStorage) HeadObject(context.Context, string) error { return nil }

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
			html_s3_key TEXT,
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

func TestPostMessage_latestHTMLKeysError_degradesGracefully(t *testing.T) {
	gdb, u := testDBWithUser(t)
	for _, ddl := range []string{
		`CREATE TABLE user_profiles (
			id TEXT PRIMARY KEY,
			user_id TEXT NOT NULL UNIQUE,
			audit_text TEXT NOT NULL DEFAULT '',
			brand_text TEXT NOT NULL DEFAULT '',
			created_at DATETIME,
			updated_at DATETIME,
			FOREIGN KEY (user_id) REFERENCES users(id)
		)`,
		`CREATE TABLE jobs (
			id TEXT PRIMARY KEY,
			chat_id TEXT NOT NULL,
			user_id TEXT NOT NULL,
			status TEXT NOT NULL,
			error_msg TEXT,
			created_at DATETIME,
			updated_at DATETIME,
			FOREIGN KEY (user_id) REFERENCES users(id),
			FOREIGN KEY (chat_id) REFERENCES chats(id)
		)`,
	} {
		require.NoError(t, gdb.Exec(ddl).Error)
	}
	require.NoError(t, gdb.Create(&db.UserProfile{
		ID:        uuid.New(),
		UserID:    u.ID,
		AuditText: "audit",
		BrandText: "brand",
	}).Error)
	repo := NewRepository(gdb)
	jobsRepo := jobs.NewRepository(gdb)
	profileRepo := profile.NewRepository(gdb)
	chat := &db.Chat{ID: uuid.New(), UserID: u.ID, PostType: db.PostTypeSingle}
	require.NoError(t, gdb.Create(chat).Error)

	var dispatched jobs.DispatchPayload
	worker := &mockDispatchWorker{
		fn: func(p *jobs.DispatchPayload) error {
			dispatched = *p
			return nil
		},
	}
	svc := NewService(repo, jobsRepo, &mockStorage{}, profileRepo, nil, worker)
	svc.latestAssistantHTMLKeys = func(context.Context, uuid.UUID) ([]string, error) {
		return nil, errors.New("simulated html keys query failure")
	}

	res, err := svc.PostMessage(context.Background(), u.ID, chat.ID, "hello world")
	require.NoError(t, err)
	require.NotNil(t, res)
	require.Nil(t, dispatched.ExistingSlideHTMLKeys)
}

func TestPostMessage_dispatchRawMessageAndExistingSlideHTMLKeys(t *testing.T) {
	gdb, u := testDBWithUser(t)
	for _, ddl := range []string{
		`CREATE TABLE user_profiles (
			id TEXT PRIMARY KEY,
			user_id TEXT NOT NULL UNIQUE,
			audit_text TEXT NOT NULL DEFAULT '',
			brand_text TEXT NOT NULL DEFAULT '',
			created_at DATETIME,
			updated_at DATETIME,
			FOREIGN KEY (user_id) REFERENCES users(id)
		)`,
		`CREATE TABLE jobs (
			id TEXT PRIMARY KEY,
			chat_id TEXT NOT NULL,
			user_id TEXT NOT NULL,
			status TEXT NOT NULL,
			error_msg TEXT,
			created_at DATETIME,
			updated_at DATETIME,
			FOREIGN KEY (user_id) REFERENCES users(id),
			FOREIGN KEY (chat_id) REFERENCES chats(id)
		)`,
	} {
		require.NoError(t, gdb.Exec(ddl).Error)
	}
	require.NoError(t, gdb.Create(&db.UserProfile{
		ID:        uuid.New(),
		UserID:    u.ID,
		AuditText: "audit",
		BrandText: "brand",
	}).Error)
	repo := NewRepository(gdb)
	jobsRepo := jobs.NewRepository(gdb)
	profileRepo := profile.NewRepository(gdb)
	chat := &db.Chat{ID: uuid.New(), UserID: u.ID, PostType: db.PostTypeSingle}
	require.NoError(t, gdb.Create(chat).Error)

	sum := "Resumo antigo: usuário pediu paleta rosa."
	require.NoError(t, gdb.Create(&db.ChatContentResume{
		ID:      uuid.New(),
		ChatID:  chat.ID,
		Summary: &sum,
	}).Error)

	require.NoError(t, gdb.Create(&db.ChatContent{
		ID:        uuid.New(),
		ChatID:    chat.ID,
		Role:      db.ChatContentRoleUser,
		Content:   "mudar só a coloração para azul",
		CreatedAt: time.Now().UTC(),
		UpdatedAt: time.Now().UTC(),
	}).Error)
	require.NoError(t, gdb.Create(&db.ChatContent{
		ID:        uuid.New(),
		ChatID:    chat.ID,
		Role:      db.ChatContentRoleAssistant,
		Content:   "Aplicando tons de azul.",
		CreatedAt: time.Now().UTC(),
		UpdatedAt: time.Now().UTC(),
	}).Error)

	var dispatched jobs.DispatchPayload
	worker := &mockDispatchWorker{
		fn: func(p *jobs.DispatchPayload) error {
			dispatched = *p
			return nil
		},
	}
	svc := NewService(repo, jobsRepo, &mockStorage{}, profileRepo, nil, worker)
	wantHTMLKeys := []string{"slides/job-id/slide1.html"}
	svc.latestAssistantHTMLKeys = func(context.Context, uuid.UUID) ([]string, error) {
		return wantHTMLKeys, nil
	}

	current := "agora cinza neutro"
	res, err := svc.PostMessage(context.Background(), u.ID, chat.ID, current)
	require.NoError(t, err)
	require.NotNil(t, res)
	require.Equal(t, current, dispatched.RawMessage)
	require.Equal(t, wantHTMLKeys, dispatched.ExistingSlideHTMLKeys)
}

func TestPostMessage_dispatchSetsExpectsSlideRefinementWhenPriorAssistantSlidesExist(t *testing.T) {
	gdb, u := testDBWithUser(t)
	for _, ddl := range []string{
		`CREATE TABLE user_profiles (
			id TEXT PRIMARY KEY,
			user_id TEXT NOT NULL UNIQUE,
			audit_text TEXT NOT NULL DEFAULT '',
			brand_text TEXT NOT NULL DEFAULT '',
			created_at DATETIME,
			updated_at DATETIME,
			FOREIGN KEY (user_id) REFERENCES users(id)
		)`,
		`CREATE TABLE jobs (
			id TEXT PRIMARY KEY,
			chat_id TEXT NOT NULL,
			user_id TEXT NOT NULL,
			status TEXT NOT NULL,
			error_msg TEXT,
			created_at DATETIME,
			updated_at DATETIME,
			FOREIGN KEY (user_id) REFERENCES users(id),
			FOREIGN KEY (chat_id) REFERENCES chats(id)
		)`,
	} {
		require.NoError(t, gdb.Exec(ddl).Error)
	}
	require.NoError(t, gdb.Create(&db.UserProfile{
		ID:        uuid.New(),
		UserID:    u.ID,
		AuditText: "audit",
		BrandText: "brand",
	}).Error)
	repo := NewRepository(gdb)
	jobsRepo := jobs.NewRepository(gdb)
	profileRepo := profile.NewRepository(gdb)
	chat := &db.Chat{ID: uuid.New(), UserID: u.ID, PostType: db.PostTypeSingle}
	require.NoError(t, gdb.Create(chat).Error)

	assistID := uuid.New()
	require.NoError(t, gdb.Create(&db.ChatContent{
		ID:        assistID,
		ChatID:    chat.ID,
		Role:      db.ChatContentRoleAssistant,
		Content:   "done",
		CreatedAt: time.Now().UTC(),
		UpdatedAt: time.Now().UTC(),
	}).Error)
	require.NoError(t, gdb.Create(&db.ChatContentImage{
		ID:            uuid.New(),
		ChatContentID: assistID,
		S3Key:         "slides/prior-job/slide01.jpeg",
		URL:           "https://example.com/preview",
		SlideNumber:   1,
		CreatedAt:     time.Now().UTC(),
		UpdatedAt:     time.Now().UTC(),
	}).Error)

	var dispatched jobs.DispatchPayload
	worker := &mockDispatchWorker{
		fn: func(p *jobs.DispatchPayload) error {
			dispatched = *p
			return nil
		},
	}
	svc := NewService(repo, jobsRepo, &mockStorage{}, profileRepo, nil, worker)

	res, err := svc.PostMessage(context.Background(), u.ID, chat.ID, "change copy only")
	require.NoError(t, err)
	require.NotNil(t, res)
	require.True(t, dispatched.ExpectsSlideRefinement, "second turn should refine when slides already exist")
}

type missingObjectStorage struct {
	mockStorage
}

func (missingObjectStorage) GetObject(context.Context, string) ([]byte, error) {
	return nil, fmt.Errorf("upstream: %w", storage.ErrObjectNotFound)
}

func TestBuildChatZip_slideMissingInStorage(t *testing.T) {
	gdb, u := testDBWithUser(t)
	repo := NewRepository(gdb)
	svc := NewService(repo, jobs.NewRepository(gdb), &missingObjectStorage{}, nil, nil, nil)
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
		URL:           "https://example.com/preview",
		SlideNumber:   1,
		CreatedAt:     time.Now().UTC(),
		UpdatedAt:     time.Now().UTC(),
	}).Error)

	_, _, err = svc.BuildChatZip(ctx, u.ID, c.ID)
	require.ErrorIs(t, err, ErrSlideStorageNotFound)
}
