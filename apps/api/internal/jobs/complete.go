package jobs

import (
	"context"
	"strings"
	"time"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/storage"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

const signedURLExpiry = time.Hour

// ArtifactRef is an S3 object produced by the worker for one slide.
type ArtifactRef struct {
	S3Key       string
	SlideNumber int
}

// CompleteAssistantReply persists the assistant message, slide images, and marks the job done.
func CompleteAssistantReply(ctx context.Context, gdb *gorm.DB, job *db.Job, assistantText string, artifacts []ArtifactRef, store storage.StorageService) error {
	return gdb.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		asst := &db.ChatContent{
			ID:      uuid.New(),
			ChatID:  job.ChatID,
			Role:    db.ChatContentRoleAssistant,
			Content: assistantText,
		}
		if err := tx.Create(asst).Error; err != nil {
			return err
		}
		for _, a := range artifacts {
			key := strings.TrimSpace(a.S3Key)
			if key == "" {
				return gorm.ErrInvalidData
			}
			if err := validateSlideArtifactKey(job.ID, key); err != nil {
				return err
			}
			url, err := store.GetSignedURL(ctx, key, signedURLExpiry)
			if err != nil {
				return err
			}
			img := db.ChatContentImage{
				ID:            uuid.New(),
				ChatContentID: asst.ID,
				S3Key:         key,
				URL:           url,
				SlideNumber:   a.SlideNumber,
			}
			if err := tx.Create(&img).Error; err != nil {
				return err
			}
		}
		return tx.Model(&db.Job{}).Where("id = ?", job.ID).Updates(map[string]interface{}{
			"status":     db.JobStatusDone,
			"error_msg":  nil,
			"updated_at": time.Now().UTC(),
		}).Error
	})
}
