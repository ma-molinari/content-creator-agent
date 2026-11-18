//go:build integration

package integration

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"content-creator-agent/internal/storage"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

type invalidArtifactStore struct {
	mockStorage
	document, manifest string
	missingSuffix      string
}

func (s invalidArtifactStore) GetObjectLimited(ctx context.Context, key string, max int64) ([]byte, string, error) {
	if strings.HasSuffix(key, s.missingSuffix) && s.missingSuffix != "" {
		return nil, "", storage.ErrObjectNotFound
	}
	if strings.HasSuffix(key, "/document.json") && s.document != "" {
		return []byte(s.document), "application/json", nil
	}
	if strings.HasSuffix(key, "/assets.json") && s.manifest != "" {
		return []byte(s.manifest), "application/json", nil
	}
	return s.mockStorage.GetObjectLimited(ctx, key, max)
}
func (s invalidArtifactStore) HeadObject(ctx context.Context, key string) error {
	if s.missingSuffix != "" && strings.HasSuffix(key, s.missingSuffix) {
		return storage.ErrObjectNotFound
	}
	return nil
}

func TestStructuredInvalidArtifactsNeverPublish(t *testing.T) {
	env := newTestEnv(t, nil)
	ctx := context.Background()
	userID, chatID := uuid.New(), uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: userID, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", userID) })
	require.NoError(t, env.DB.Create(&db.Chat{ID: chatID, UserID: userID, PostType: db.PostTypeSingle, PostFormat: db.PostFormatStructuredV1}).Error)
	imageDocument := `{"schemaVersion":1,"postType":"single","slides":[{"id":"s","layout":"hero","background":{"type":"solid","color":"#000000"},"elements":[{"id":"i","type":"image","assetId":"asset1","fit":"cover"}]}]}`
	for _, tc := range []struct {
		name  string
		store invalidArtifactStore
	}{
		{"documento ausente", invalidArtifactStore{missingSuffix: "/document.json"}},
		{"manifesto ausente", invalidArtifactStore{missingSuffix: "/assets.json"}},
		{"imagem ausente", invalidArtifactStore{missingSuffix: "/slide_01.jpeg"}},
		{"documento inválido", invalidArtifactStore{document: `{"schemaVersion":1,"postType":"single","slides":[{}]}`}},
		{"asset de outro job", invalidArtifactStore{document: imageDocument, manifest: `{"asset1":"slides/00000000-0000-0000-0000-000000000000/assets/asset1.png"}`}},
		{"asset sem manifesto", invalidArtifactStore{document: imageDocument}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			jobID := uuid.New()
			mode := "create"
			require.NoError(t, env.DB.Create(&db.Job{ID: jobID, ChatID: chatID, UserID: userID, Status: db.JobStatusProcessing, PostFormat: db.PostFormatStructuredV1, GenerationMode: &mode}).Error)
			prefix := fmt.Sprintf("slides/%s/", jobID)
			html := prefix + "slide_01.html"
			_, _, err := jobs.CompleteStructuredReply(ctx, env.DB, jobID, "ok", []jobs.ArtifactRef{{S3Key: prefix + "slide_01.jpeg", HtmlS3Key: &html, SlideNumber: 1}}, jobs.StructuredArtifact{DocumentS3Key: prefix + "document.json", SchemaVersion: 1, RendererVersion: "1"}, tc.store)
			require.Error(t, err)
			var count int64
			require.NoError(t, env.DB.Model(&db.PostVersion{}).Where("chat_id = ?", chatID).Count(&count).Error)
			require.Zero(t, count)
			var row db.Chat
			require.NoError(t, env.DB.First(&row, "id = ?", chatID).Error)
			require.Nil(t, row.CurrentVersionID)
			var job db.Job
			require.NoError(t, env.DB.First(&job, "id = ?", jobID).Error)
			require.Equal(t, db.JobStatusProcessing, job.Status)
		})
	}
}
