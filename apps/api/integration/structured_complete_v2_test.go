//go:build integration

package integration

import (
	"context"
	"fmt"
	"sync"
	"testing"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

const validV2 = `{"schemaVersion":2,"postType":"single","palette":{"background":"#ffffff","text":"#000000","accent":"#ff0000"},"slides":[{"id":"s","layout":"hero","background":{"type":"solid","color":{"token":"background"}},"elements":[{"id":"b","type":"decoration","kind":"bar","color":{"token":"accent"},"width":"full","thickness":"medium","corner":"rounded"},{"id":"t","type":"text","role":"heading","content":"Olá","style":{"color":{"token":"text"},"size":"large"}}]}]}`

func TestStructuredV2CompletionChecksTargetAndIsIdempotent(t *testing.T) {
	env := newTestEnv(t, nil)
	ctx := context.Background()
	user, chatID, jobID := uuid.New(), uuid.New(), uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: user, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", user) })
	require.NoError(t, env.DB.Create(&db.Chat{ID: chatID, UserID: user, PostType: db.PostTypeSingle, PostFormat: db.PostFormatStructuredV1}).Error)
	mode, target := "create", 2
	require.NoError(t, env.DB.Create(&db.Job{ID: jobID, ChatID: chatID, UserID: user, Status: db.JobStatusProcessing, PostFormat: db.PostFormatStructuredV1, GenerationMode: &mode, TargetSchemaVersion: &target}).Error)
	prefix := fmt.Sprintf("slides/%s/", jobID)
	html := prefix + "slide_01.html"
	artifacts := []jobs.ArtifactRef{{S3Key: prefix + "slide_01.jpeg", HtmlS3Key: &html, SlideNumber: 1}}
	source := jobs.StructuredArtifact{DocumentS3Key: prefix + "document.json", SchemaVersion: 1, RendererVersion: "1.0.0"}
	_, _, err := jobs.CompleteStructuredReply(ctx, env.DB, jobID, "ok", artifacts, source, invalidArtifactStore{document: validV2})
	require.Error(t, err)
	var row db.Chat
	require.NoError(t, env.DB.First(&row, "id = ?", chatID).Error)
	require.Nil(t, row.CurrentVersionID)
	source.SchemaVersion, source.RendererVersion = 2, "2.0.0"
	_, _, err = jobs.CompleteStructuredReply(ctx, env.DB, jobID, "ok", artifacts, source, invalidArtifactStore{document: `{"schemaVersion":2}`})
	require.Error(t, err)
	done, conflict, err := jobs.CompleteStructuredReply(ctx, env.DB, jobID, "ok", artifacts, source, invalidArtifactStore{document: validV2})
	require.NoError(t, err)
	require.False(t, done)
	require.False(t, conflict)
	var version db.PostVersion
	require.NoError(t, env.DB.Where("job_id = ?", jobID).First(&version).Error)
	require.Equal(t, 2, version.SchemaVersion)
	done, conflict, err = jobs.CompleteStructuredReply(ctx, env.DB, jobID, "repetido", nil, jobs.StructuredArtifact{}, invalidArtifactStore{missingSuffix: "/document.json"})
	require.NoError(t, err)
	require.True(t, done)
	require.False(t, conflict)
	var count int64
	require.NoError(t, env.DB.Model(&db.PostVersion{}).Where("chat_id = ?", chatID).Count(&count).Error)
	require.EqualValues(t, 1, count)
}

func TestStructuredV2FirstVersionRace(t *testing.T) {
	env := newTestEnv(t, nil)
	user, chatID := uuid.New(), uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: user, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", user) })
	require.NoError(t, env.DB.Create(&db.Chat{ID: chatID, UserID: user, PostType: db.PostTypeSingle, PostFormat: db.PostFormatStructuredV1}).Error)
	mode, target := "create", 2
	ids := []uuid.UUID{uuid.New(), uuid.New()}
	for _, id := range ids {
		require.NoError(t, env.DB.Create(&db.Job{ID: id, ChatID: chatID, UserID: user, Status: db.JobStatusProcessing, PostFormat: db.PostFormatStructuredV1, GenerationMode: &mode, TargetSchemaVersion: &target}).Error)
	}
	type result struct {
		conflict bool
		err      error
	}
	results := make([]result, 2)
	var wg sync.WaitGroup
	for i, id := range ids {
		wg.Add(1)
		go func(i int, id uuid.UUID) {
			defer wg.Done()
			prefix := fmt.Sprintf("slides/%s/", id)
			html := prefix + "slide_01.html"
			_, results[i].conflict, results[i].err = jobs.CompleteStructuredReply(context.Background(), env.DB, id, "ok", []jobs.ArtifactRef{{S3Key: prefix + "slide_01.jpeg", HtmlS3Key: &html, SlideNumber: 1}}, jobs.StructuredArtifact{DocumentS3Key: prefix + "document.json", SchemaVersion: 2, RendererVersion: "2.0.0"}, invalidArtifactStore{document: validV2})
		}(i, id)
	}
	wg.Wait()
	require.NoError(t, results[0].err)
	require.NoError(t, results[1].err)
	require.NotEqual(t, results[0].conflict, results[1].conflict)
}

func TestOldStructuredJobDoesNotAcceptV2Callback(t *testing.T) {
	env := newTestEnv(t, nil)
	user, chatID, jobID := uuid.New(), uuid.New(), uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: user, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", user) })
	require.NoError(t, env.DB.Create(&db.Chat{ID: chatID, UserID: user, PostType: db.PostTypeSingle, PostFormat: db.PostFormatStructuredV1}).Error)
	mode := "create"
	require.NoError(t, env.DB.Create(&db.Job{ID: jobID, ChatID: chatID, UserID: user, Status: db.JobStatusProcessing, PostFormat: db.PostFormatStructuredV1, GenerationMode: &mode}).Error)
	prefix := fmt.Sprintf("slides/%s/", jobID)
	html := prefix + "slide_01.html"
	artifacts := []jobs.ArtifactRef{{S3Key: prefix + "slide_01.jpeg", HtmlS3Key: &html, SlideNumber: 1}}
	_, _, err := jobs.CompleteStructuredReply(context.Background(), env.DB, jobID, "ok", artifacts, jobs.StructuredArtifact{DocumentS3Key: prefix + "document.json", SchemaVersion: 2, RendererVersion: "2.0.0"}, invalidArtifactStore{document: validV2})
	require.Error(t, err)
	var chat db.Chat
	require.NoError(t, env.DB.First(&chat, "id = ?", chatID).Error)
	require.Nil(t, chat.CurrentVersionID)
}
