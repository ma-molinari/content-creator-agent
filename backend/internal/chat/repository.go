package chat

import (
	"context"
	"errors"

	"content-creator-agent/internal/db"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// Repository persists chat aggregates.
type Repository struct {
	db *gorm.DB
}

// NewRepository constructs a chat repository.
func NewRepository(gdb *gorm.DB) *Repository {
	return &Repository{db: gdb}
}

// ListByUser returns up to limit chats for the user, newest first.
func (r *Repository) ListByUser(ctx context.Context, userID uuid.UUID, limit int) ([]db.Chat, error) {
	var chats []db.Chat
	err := r.db.WithContext(ctx).
		Where("user_id = ?", userID).
		Order("created_at DESC").
		Limit(limit).
		Find(&chats).Error
	return chats, err
}

// CountByUser returns how many chats the user has.
func (r *Repository) CountByUser(ctx context.Context, userID uuid.UUID) (int64, error) {
	var n int64
	err := r.db.WithContext(ctx).Model(&db.Chat{}).Where("user_id = ?", userID).Count(&n).Error
	return n, err
}

// OldestChatID returns the id of the user's oldest chat by created_at.
func (r *Repository) OldestChatID(ctx context.Context, userID uuid.UUID) (uuid.UUID, error) {
	var c db.Chat
	err := r.db.WithContext(ctx).
		Where("user_id = ?", userID).
		Order("created_at ASC").
		First(&c).Error
	if err != nil {
		return uuid.Nil, err
	}
	return c.ID, nil
}

// Create inserts a new chat row.
func (r *Repository) Create(ctx context.Context, userID uuid.UUID, postType db.PostType) (*db.Chat, error) {
	c := db.Chat{
		ID:       uuid.New(),
		UserID:   userID,
		PostType: postType,
	}
	if err := r.db.WithContext(ctx).Create(&c).Error; err != nil {
		return nil, err
	}
	return &c, nil
}

// GetByID loads a chat by primary key only (no ownership check).
func (r *Repository) GetByID(ctx context.Context, id uuid.UUID) (*db.Chat, error) {
	var c db.Chat
	err := r.db.WithContext(ctx).First(&c, "id = ?", id).Error
	if err != nil {
		return nil, err
	}
	return &c, nil
}

// GetByIDWithContents loads chat with ordered contents and images.
func (r *Repository) GetByIDWithContents(ctx context.Context, id uuid.UUID) (*db.Chat, error) {
	var c db.Chat
	err := r.db.WithContext(ctx).
		Preload("Contents", func(g *gorm.DB) *gorm.DB {
			return g.Order("chat_content.created_at ASC")
		}).
		Preload("Contents.Images", func(g *gorm.DB) *gorm.DB {
			return g.Order("chat_content_image.slide_number ASC")
		}).
		Preload("Resume").
		First(&c, "id = ?", id).Error
	if err != nil {
		return nil, err
	}
	return &c, nil
}

// CollectS3KeysForChat returns all s3_key values for images in the chat.
func (r *Repository) CollectS3KeysForChat(ctx context.Context, chatID uuid.UUID) ([]string, error) {
	var keys []string
	sub := r.db.WithContext(ctx).Model(&db.ChatContent{}).Select("id").Where("chat_id = ?", chatID)
	err := r.db.WithContext(ctx).Model(&db.ChatContentImage{}).
		Where("chat_content_id IN (?)", sub).
		Pluck("s3_key", &keys).Error
	return keys, err
}

// DeleteChat hard-deletes the chat row (DB cascades to related rows).
func (r *Repository) DeleteChat(ctx context.Context, chatID uuid.UUID) error {
	res := r.db.WithContext(ctx).Unscoped().Delete(&db.Chat{}, "id = ?", chatID)
	if res.Error != nil {
		return res.Error
	}
	if res.RowsAffected == 0 {
		return gorm.ErrRecordNotFound
	}
	return nil
}

// ListImagesForChat returns all images for a chat ordered by slide number.
func (r *Repository) ListImagesForChat(ctx context.Context, chatID uuid.UUID) ([]db.ChatContentImage, error) {
	var imgs []db.ChatContentImage
	err := r.db.WithContext(ctx).
		Joins("JOIN chat_content ON chat_content.id = chat_content_image.chat_content_id").
		Where("chat_content.chat_id = ?", chatID).
		Order("chat_content_image.slide_number ASC").
		Find(&imgs).Error
	return imgs, err
}

// GetImageInChat loads an image by id ensuring it belongs to chatID.
func (r *Repository) GetImageInChat(ctx context.Context, chatID, imageID uuid.UUID) (*db.ChatContentImage, error) {
	var img db.ChatContentImage
	err := r.db.WithContext(ctx).Model(&db.ChatContentImage{}).
		Joins("JOIN chat_content ON chat_content.id = chat_content_image.chat_content_id").
		Where("chat_content_image.id = ? AND chat_content.chat_id = ?", imageID, chatID).
		First(&img).Error
	if err != nil {
		return nil, err
	}
	return &img, nil
}

// ErrRecordNotFound wraps gorm.ErrRecordNotFound for callers.
func ErrRecordNotFound(err error) bool {
	return errors.Is(err, gorm.ErrRecordNotFound)
}
