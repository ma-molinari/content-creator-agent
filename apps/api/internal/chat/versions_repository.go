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
