package chat

import (
	"context"
	"encoding/json"

	"content-creator-agent/internal/db"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

type cleanupTask struct {
	ID         uuid.UUID `gorm:"type:uuid;primaryKey"`
	ChatID     uuid.UUID `gorm:"type:uuid;uniqueIndex;not null"`
	ObjectKeys string    `gorm:"not null"`
	JobIDs     string    `gorm:"not null"`
}

func (cleanupTask) TableName() string { return "chat_cleanup_tasks" }

// captureChatCleanup persists object keys and job prefixes before cascade deletes their source rows.
func captureChatCleanup(ctx context.Context, tx *gorm.DB, chatID uuid.UUID) ([]string, error) {
	repo := NewRepository(tx)
	keys, err := repo.CollectS3KeysForChat(ctx, chatID)
	if err != nil {
		return nil, err
	}
	var documentKeys []string
	if err := tx.WithContext(ctx).Model(&db.PostVersion{}).Where("chat_id = ?", chatID).Pluck("document_s3_key", &documentKeys).Error; err != nil {
		return nil, err
	}
	keys = append(keys, documentKeys...)
	var jobIDs []uuid.UUID
	if err := tx.WithContext(ctx).Model(&db.Job{}).Where("chat_id = ?", chatID).Pluck("id", &jobIDs).Error; err != nil {
		return nil, err
	}
	if keys == nil {
		keys = []string{}
	}
	if jobIDs == nil {
		jobIDs = []uuid.UUID{}
	}
	serializedKeys, err := json.Marshal(keys)
	if err != nil {
		return nil, err
	}
	serializedJobs, err := json.Marshal(jobIDs)
	if err != nil {
		return nil, err
	}
	task := cleanupTask{ID: uuid.New(), ChatID: chatID, ObjectKeys: string(serializedKeys), JobIDs: string(serializedJobs)}
	if err := tx.WithContext(ctx).Create(&task).Error; err != nil {
		return nil, err
	}
	return keys, nil
}

// DeleteOwnedChatWithCleanup records cleanup before deleting the owned chat and its dependents.
func (r *Repository) DeleteOwnedChatWithCleanup(ctx context.Context, userID, chatID uuid.UUID) ([]string, error) {
	var keys []string
	err := r.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		if _, err := r.LockOwnedChat(ctx, tx, userID, chatID); err != nil {
			return err
		}
		var err error
		keys, err = captureChatCleanup(ctx, tx, chatID)
		if err != nil {
			return err
		}
		return tx.Unscoped().Delete(&db.Chat{}, "id = ?", chatID).Error
	})
	return keys, err
}

// CleanupKeys reads the durable inventory even after the chat has been deleted.
func (r *Repository) CleanupKeys(ctx context.Context, chatID uuid.UUID) ([]string, error) {
	var task cleanupTask
	if err := r.db.WithContext(ctx).Where("chat_id = ?", chatID).First(&task).Error; err != nil {
		return nil, err
	}
	var keys []string
	if err := json.Unmarshal([]byte(task.ObjectKeys), &keys); err != nil {
		return nil, err
	}
	return keys, nil
}
