package chat

import (
	"context"
	"errors"
	"strings"

	"content-creator-agent/internal/db"

	"github.com/google/uuid"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
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

// CreateChatEvicting atomically counts the user's chats, evicts the oldest when
// the count is at or above the limit, and inserts the new chat — all inside a
// single serialisable transaction to prevent TOCTOU races.
// It returns the new chat and, when an eviction occurred, the evicted chat ID
// so the caller can clean up S3 artefacts outside the transaction.
func (r *Repository) CreateChatEvicting(ctx context.Context, userID uuid.UUID, postType db.PostType, limit int) (*db.Chat, *uuid.UUID, error) {
	var created db.Chat
	var evictedID *uuid.UUID

	err := r.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		var ids []uuid.UUID
		// clause.Locking is silently ignored by the SQLite driver (unit tests) and
		// translates to FOR UPDATE on PostgreSQL (production).
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).
			Model(&db.Chat{}).
			Where("user_id = ?", userID).
			Order("created_at ASC").
			Pluck("id", &ids).Error; err != nil {
			return err
		}
		if len(ids) >= limit {
			oldest := ids[0]
			evictedID = &oldest
			if err := tx.Unscoped().Delete(&db.Chat{}, "id = ?", oldest).Error; err != nil {
				return err
			}
		}
		created = db.Chat{ID: uuid.New(), UserID: userID, PostType: postType}
		return tx.Create(&created).Error
	})
	if err != nil {
		return nil, nil, err
	}
	return &created, evictedID, nil
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

// ListImagesForChat returns all images for a chat: chronological assistant turns,
// then slide order within each turn (by chat_content.created_at, id, slide_number).
func (r *Repository) ListImagesForChat(ctx context.Context, chatID uuid.UUID) ([]db.ChatContentImage, error) {
	var imgs []db.ChatContentImage
	err := r.db.WithContext(ctx).
		Joins("JOIN chat_content ON chat_content.id = chat_content_image.chat_content_id").
		Where("chat_content.chat_id = ?", chatID).
		Order("chat_content.created_at ASC, chat_content.id ASC, chat_content_image.slide_number ASC").
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

// ListContentsOrdered returns chat messages in chronological order.
func (r *Repository) ListContentsOrdered(ctx context.Context, chatID uuid.UUID) ([]db.ChatContent, error) {
	var rows []db.ChatContent
	err := r.db.WithContext(ctx).
		Where("chat_id = ?", chatID).
		Order("created_at ASC").
		Find(&rows).Error
	return rows, err
}

// GetResumeByChatID returns the resume row when present.
func (r *Repository) GetResumeByChatID(ctx context.Context, chatID uuid.UUID) (*db.ChatContentResume, error) {
	var res db.ChatContentResume
	err := r.db.WithContext(ctx).Where("chat_id = ?", chatID).First(&res).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &res, nil
}

// CreateContentWithImages inserts the user message, assistant message, and slide images in one transaction.
func (r *Repository) CreateContentWithImages(ctx context.Context, userContent *db.ChatContent, assistantContent *db.ChatContent, images []db.ChatContentImage) error {
	return r.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		if err := tx.Create(userContent).Error; err != nil {
			return err
		}
		if err := tx.Create(assistantContent).Error; err != nil {
			return err
		}
		for i := range images {
			images[i].ChatContentID = assistantContent.ID
			if err := tx.Create(&images[i]).Error; err != nil {
				return err
			}
		}
		return nil
	})
}

// CreateUserMessageAndJob inserts the user message row and a job (caller sets status, e.g. processing) in one transaction.
// When setTitle is non-empty, updates the chat title only if it is still unset (NULL or blank).
func (r *Repository) CreateUserMessageAndJob(ctx context.Context, userContent *db.ChatContent, job *db.Job, setTitle *string) error {
	return r.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		if err := tx.Create(userContent).Error; err != nil {
			return err
		}
		if err := tx.Create(job).Error; err != nil {
			return err
		}
		if setTitle != nil {
			preview := strings.TrimSpace(*setTitle)
			if preview != "" {
				res := tx.Model(&db.Chat{}).
					Where("id = ?", userContent.ChatID).
					Where("(title IS NULL OR TRIM(COALESCE(title, '')) = '')").
					Update("title", preview)
				if res.Error != nil {
					return res.Error
				}
			}
		}
		return nil
	})
}

// GetJobForChat loads a job when it belongs to the given user and chat.
func (r *Repository) GetJobForChat(ctx context.Context, userID, chatID, jobID uuid.UUID) (*db.Job, error) {
	var j db.Job
	err := r.db.WithContext(ctx).First(&j, "id = ? AND user_id = ? AND chat_id = ?", jobID, userID, chatID).Error
	if err != nil {
		return nil, err
	}
	return &j, nil
}
