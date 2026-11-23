package chat

import (
	"context"

	"content-creator-agent/internal/db"
	"github.com/google/uuid"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

// LockOwnedChat must be called with an active transaction; locks serialize version publication.
func (r *Repository) LockOwnedChat(ctx context.Context, tx *gorm.DB, userID, chatID uuid.UUID) (*db.Chat, error) {
	var row db.Chat
	err := tx.WithContext(ctx).Clauses(clause.Locking{Strength: "UPDATE"}).
		Where("id = ? AND user_id = ?", chatID, userID).First(&row).Error
	if err != nil {
		return nil, err
	}
	return &row, nil
}

// ListVersions returns the full history for an owned chat. Missing and unauthorized chats return ErrRecordNotFound.
func (r *Repository) ListVersions(ctx context.Context, userID, chatID uuid.UUID) ([]db.PostVersion, error) {
	var row db.Chat
	if err := r.db.WithContext(ctx).Where("id = ? AND user_id = ?", chatID, userID).First(&row).Error; err != nil {
		return nil, err
	}
	var versions []db.PostVersion
	err := r.db.WithContext(ctx).Where("chat_id = ?", chatID).
		Order("created_at ASC").Order("id ASC").Find(&versions).Error
	return versions, err
}

// GetOwnedVersion returns a version only when it belongs to the given user's chat.
func (r *Repository) GetOwnedVersion(ctx context.Context, userID, chatID, versionID uuid.UUID) (*db.PostVersion, error) {
	var version db.PostVersion
	err := r.db.WithContext(ctx).Model(&db.PostVersion{}).
		Joins("JOIN chats ON chats.id = post_versions.chat_id").
		Where("post_versions.id = ? AND post_versions.chat_id = ? AND chats.user_id = ?", versionID, chatID, userID).
		First(&version).Error
	if err != nil {
		return nil, err
	}
	return &version, nil
}

// GetCurrentVersion returns nil when the owned chat has no structured version yet.
func (r *Repository) GetCurrentVersion(ctx context.Context, userID, chatID uuid.UUID) (*db.PostVersion, error) {
	var row db.Chat
	if err := r.db.WithContext(ctx).Where("id = ? AND user_id = ?", chatID, userID).First(&row).Error; err != nil {
		return nil, err
	}
	if row.CurrentVersionID == nil {
		return nil, nil
	}
	return r.GetOwnedVersion(ctx, userID, chatID, *row.CurrentVersionID)
}

// CreateStructuredMessageAndJob captures the current base under the chat lock.
func (r *Repository) CreateStructuredMessageAndJob(ctx context.Context, userID uuid.UUID, content *db.ChatContent, job *db.Job, mode string, requestedBase *uuid.UUID, setTitle *string, attachments []db.ChatContentAttachment, v2Enabled, v2MutationsDisabled bool, v2Ready func(context.Context, int) bool) (string, error) {
	var documentKey string
	err := r.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		row, err := r.LockOwnedChat(ctx, tx, userID, content.ChatID)
		if err != nil {
			return err
		}
		if row.PostFormat != db.PostFormatStructuredV1 {
			return ErrInvalidStructuredMode
		}
		targetSchema, readSchema := 1, 0
		if mode == "edit" {
			if requestedBase == nil || row.CurrentVersionID == nil || *requestedBase != *row.CurrentVersionID {
				return ErrVersionConflict
			}
			var base db.PostVersion
			if err := tx.Where("id = ? AND chat_id = ?", *requestedBase, row.ID).First(&base).Error; err != nil {
				return err
			}
			documentKey = base.DocumentS3Key
			readSchema = base.SchemaVersion
			if readSchema != 1 && readSchema != 2 {
				return ErrStructuredUnavailable
			}
		}
		if v2Enabled || readSchema == 2 {
			targetSchema = 2
			if v2MutationsDisabled || v2Ready == nil || !v2Ready(ctx, readSchema) {
				return ErrStructuredUnavailable
			}
		}
		job.PostFormat = db.PostFormatStructuredV1
		job.TargetSchemaVersion = &targetSchema
		job.GenerationMode = &mode
		job.ExpectedVersionID = row.CurrentVersionID
		if err := tx.Create(content).Error; err != nil {
			return err
		}
		for i := range attachments {
			attachments[i].ChatContentID = content.ID
		}
		if len(attachments) > 0 {
			if err := tx.Create(&attachments).Error; err != nil {
				return err
			}
		}
		if err := tx.Create(job).Error; err != nil {
			return err
		}
		if setTitle != nil && *setTitle != "" {
			if err := tx.Model(&db.Chat{}).Where("id = ? AND (title IS NULL OR TRIM(COALESCE(title, '')) = '')", row.ID).Update("title", *setTitle).Error; err != nil {
				return err
			}
		}
		return nil
	})
	return documentKey, err
}
