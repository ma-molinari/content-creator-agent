package chat

import (
	"context"
	"testing"
	"time"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

func testRepoWithUserChatAndJobsTable(t *testing.T) (*Repository, *db.User, *db.Chat, *gorm.DB) {
	t.Helper()
	gdb, u := testDBWithUser(t)
	jobsDDL := `CREATE TABLE jobs (
		id TEXT PRIMARY KEY,
		chat_id TEXT NOT NULL,
		user_id TEXT NOT NULL,
		status TEXT NOT NULL,
		error_msg TEXT,
		created_at DATETIME,
		updated_at DATETIME
	)`
	if err := gdb.Exec(jobsDDL).Error; err != nil {
		t.Fatal(err)
	}
	repo := NewRepository(gdb)
	c := &db.Chat{ID: uuid.New(), UserID: u.ID, PostType: db.PostTypeSingle}
	if err := gdb.Create(c).Error; err != nil {
		t.Fatal(err)
	}
	return repo, u, c, gdb
}

func TestCreateUserMessageAndJob_setsTitleWhenEmpty(t *testing.T) {
	repo, u, chat, gdb := testRepoWithUserChatAndJobsTable(t)
	ctx := context.Background()
	body := "First message preview should land in title"
	preview := titlePreviewFromBody(body)
	userMsg := &db.ChatContent{
		ID:      uuid.New(),
		ChatID:  chat.ID,
		Role:    db.ChatContentRoleUser,
		Content: body,
	}
	job := &db.Job{
		ID:        uuid.New(),
		ChatID:    chat.ID,
		UserID:    u.ID,
		Status:    db.JobStatusPending,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}
	if err := repo.CreateUserMessageAndJob(ctx, userMsg, job, &preview); err != nil {
		t.Fatal(err)
	}
	var reloaded db.Chat
	if err := gdb.First(&reloaded, "id = ?", chat.ID).Error; err != nil {
		t.Fatal(err)
	}
	if reloaded.Title == nil || *reloaded.Title != preview {
		t.Fatalf("title: got %v want %q", reloaded.Title, preview)
	}
}

func TestCreateUserMessageAndJob_doesNotOverwriteExistingTitle(t *testing.T) {
	repo, u, chat, gdb := testRepoWithUserChatAndJobsTable(t)
	ctx := context.Background()
	existing := "Kept title"
	if err := gdb.Model(&db.Chat{}).Where("id = ?", chat.ID).Update("title", existing).Error; err != nil {
		t.Fatal(err)
	}
	body := "Second message"
	preview := titlePreviewFromBody(body)
	userMsg := &db.ChatContent{
		ID:      uuid.New(),
		ChatID:  chat.ID,
		Role:    db.ChatContentRoleUser,
		Content: body,
	}
	job := &db.Job{
		ID:        uuid.New(),
		ChatID:    chat.ID,
		UserID:    u.ID,
		Status:    db.JobStatusPending,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}
	if err := repo.CreateUserMessageAndJob(ctx, userMsg, job, &preview); err != nil {
		t.Fatal(err)
	}
	var reloaded db.Chat
	if err := gdb.First(&reloaded, "id = ?", chat.ID).Error; err != nil {
		t.Fatal(err)
	}
	if reloaded.Title == nil || *reloaded.Title != existing {
		t.Fatalf("title: got %v want %q", reloaded.Title, existing)
	}
}

func TestCreateUserMessageAndJob_nilSetTitleNoUpdate(t *testing.T) {
	repo, u, chat, gdb := testRepoWithUserChatAndJobsTable(t)
	ctx := context.Background()
	userMsg := &db.ChatContent{
		ID:      uuid.New(),
		ChatID:  chat.ID,
		Role:    db.ChatContentRoleUser,
		Content: "x",
	}
	job := &db.Job{
		ID:        uuid.New(),
		ChatID:    chat.ID,
		UserID:    u.ID,
		Status:    db.JobStatusPending,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}
	if err := repo.CreateUserMessageAndJob(ctx, userMsg, job, nil); err != nil {
		t.Fatal(err)
	}
	var reloaded db.Chat
	if err := gdb.First(&reloaded, "id = ?", chat.ID).Error; err != nil {
		t.Fatal(err)
	}
	if reloaded.Title != nil {
		t.Fatalf("expected nil title, got %v", *reloaded.Title)
	}
}

func TestCreateUserMessageAndJob_createsJobRow(t *testing.T) {
	repo, u, chat, gdb := testRepoWithUserChatAndJobsTable(t)
	ctx := context.Background()
	jobsRepo := jobs.NewRepository(gdb)
	jobID := uuid.New()
	userMsg := &db.ChatContent{
		ID:      uuid.New(),
		ChatID:  chat.ID,
		Role:    db.ChatContentRoleUser,
		Content: "hello",
	}
	job := &db.Job{
		ID:        jobID,
		ChatID:    chat.ID,
		UserID:    u.ID,
		Status:    db.JobStatusPending,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}
	if err := repo.CreateUserMessageAndJob(ctx, userMsg, job, nil); err != nil {
		t.Fatal(err)
	}
	j, err := jobsRepo.GetByID(ctx, jobID)
	if err != nil {
		t.Fatal(err)
	}
	if j.Status != db.JobStatusPending {
		t.Fatalf("job status: %s", j.Status)
	}
}

func TestListImagesForChat_ordersByTurnThenSlide(t *testing.T) {
	gdb, u := testDBWithUser(t)
	repo := NewRepository(gdb)
	chat := &db.Chat{ID: uuid.New(), UserID: u.ID, PostType: db.PostTypeSingle}
	if err := gdb.Create(chat).Error; err != nil {
		t.Fatal(err)
	}
	early := time.Date(2020, 1, 1, 12, 0, 0, 0, time.UTC)
	later := time.Date(2020, 1, 2, 12, 0, 0, 0, time.UTC)
	turn1ID := uuid.New()
	turn2ID := uuid.New()
	turn1 := &db.ChatContent{
		ID:        turn1ID,
		ChatID:    chat.ID,
		Role:      db.ChatContentRoleAssistant,
		Content:   "a1",
		CreatedAt: early,
	}
	turn2 := &db.ChatContent{
		ID:        turn2ID,
		ChatID:    chat.ID,
		Role:      db.ChatContentRoleAssistant,
		Content:   "a2",
		CreatedAt: later,
	}
	if err := gdb.Create(turn1).Error; err != nil {
		t.Fatal(err)
	}
	if err := gdb.Create(turn2).Error; err != nil {
		t.Fatal(err)
	}
	// Same slide numbers in both turns (ZIP used to collapse these).
	imgs := []db.ChatContentImage{
		{ID: uuid.New(), ChatContentID: turn1ID, S3Key: "k1a", URL: "u1a", SlideNumber: 1},
		{ID: uuid.New(), ChatContentID: turn1ID, S3Key: "k1b", URL: "u1b", SlideNumber: 2},
		{ID: uuid.New(), ChatContentID: turn2ID, S3Key: "k2a", URL: "u2a", SlideNumber: 1},
		{ID: uuid.New(), ChatContentID: turn2ID, S3Key: "k2b", URL: "u2b", SlideNumber: 2},
	}
	if err := gdb.Create(&imgs).Error; err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	got, err := repo.ListImagesForChat(ctx, chat.ID)
	if err != nil {
		t.Fatal(err)
	}
	if len(got) != 4 {
		t.Fatalf("len: %d", len(got))
	}
	for i, wantID := range []uuid.UUID{turn1ID, turn1ID, turn2ID, turn2ID} {
		if got[i].ChatContentID != wantID {
			t.Fatalf("row %d chat_content_id: got %s want %s", i, got[i].ChatContentID, wantID)
		}
	}
	if got[0].S3Key != "k1a" || got[1].S3Key != "k1b" || got[2].S3Key != "k2a" || got[3].S3Key != "k2b" {
		t.Fatalf("order: %#v", got)
	}
}
