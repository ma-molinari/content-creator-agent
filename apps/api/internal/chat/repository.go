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
		Preload("Contents.Attachments", func(g *gorm.DB) *gorm.DB {
			return g.Order("chat_content_attachment.sort_order ASC")
		}).
		Preload("Resume").
		First(&c, "id = ?", id).Error
	if err != nil {
		return nil, err
	}
	return &c, nil
}

// CollectS3KeysForChat returns all s3_key values for images in the chat,
// plus distinct html_s3_key values when set (for eviction/delete cleanup).
func (r *Repository) CollectS3KeysForChat(ctx context.Context, chatID uuid.UUID) ([]string, error) {
	var keys []string
	sub := r.db.WithContext(ctx).Model(&db.ChatContent{}).Select("id").Where("chat_id = ?", chatID)
	if err := r.db.WithContext(ctx).Model(&db.ChatContentImage{}).
		Where("chat_content_id IN (?)", sub).
		Pluck("s3_key", &keys).Error; err != nil {
		return nil, err
	}
	var htmlKeys []string
	if err := r.db.WithContext(ctx).Model(&db.ChatContentImage{}).
		Where("chat_content_id IN (?) AND html_s3_key IS NOT NULL AND html_s3_key != ''", sub).
		Pluck("html_s3_key", &htmlKeys).Error; err != nil {
		return nil, err
	}
	seen := make(map[string]struct{}, len(keys)+len(htmlKeys))
	out := make([]string, 0, len(keys)+len(htmlKeys))
	for _, k := range keys {
		if _, ok := seen[k]; ok {
			continue
		}
		seen[k] = struct{}{}
		out = append(out, k)
	}
	for _, k := range htmlKeys {
		if _, ok := seen[k]; ok {
			continue
		}
		seen[k] = struct{}{}
		out = append(out, k)
	}
	var attachKeys []string
	if err := r.db.WithContext(ctx).Model(&db.ChatContentAttachment{}).
		Where("chat_content_id IN (?)", sub).
		Pluck("s3_key", &attachKeys).Error; err != nil {
		return nil, err
	}
	for _, k := range attachKeys {
		if _, ok := seen[k]; ok {
			continue
		}
		seen[k] = struct{}{}
		out = append(out, k)
	}
	return out, nil
}

// ChatHasAssistantWithSlideArtifacts is true when the chat already has at least one JPEG
// slide persisted for an assistant turn (prior generation vs this dispatch).
func (r *Repository) ChatHasAssistantWithSlideArtifacts(ctx context.Context, chatID uuid.UUID) (bool, error) {
	type row struct {
		One int `gorm:"column:one"`
	}
	var probe row
	dbErr := r.db.WithContext(ctx).
		Table("chat_content_image").
		Select("1 AS one").
		Joins("INNER JOIN chat_content ON chat_content.id = chat_content_image.chat_content_id").
		Where("chat_content.chat_id = ?", chatID).
		Where("chat_content.role = ?", db.ChatContentRoleAssistant).
		Where(`LENGTH(TRIM(COALESCE(chat_content_image.s3_key, ''))) > 0`).
		Limit(1).
		Take(&probe).Error
	if errors.Is(dbErr, gorm.ErrRecordNotFound) {
		return false, nil
	}
	if dbErr != nil {
		return false, dbErr
	}
	return true, nil
}

// GetLatestAssistantHTMLKeys returns html_s3_key values from the newest assistant turn
// that has at least one non-empty html_s3_key, ordered by slide_number.
func (r *Repository) GetLatestAssistantHTMLKeys(ctx context.Context, chatID uuid.UUID) ([]string, error) {
	var htmlKeys []string
	err := r.db.WithContext(ctx).Raw(`
		WITH turns_with_html AS (
			SELECT cc.id, cc.created_at
			FROM chat_content cc
			INNER JOIN chat_content_image cci ON cci.chat_content_id = cc.id
			WHERE cc.chat_id = ? AND cc.role = ?
				AND LENGTH(TRIM(COALESCE(cci.html_s3_key, ''))) > 0
			GROUP BY cc.id, cc.created_at
		),
		newest AS (
			SELECT id FROM turns_with_html ORDER BY created_at DESC, id DESC LIMIT 1
		)
		SELECT cci.html_s3_key
		FROM chat_content_image cci
		WHERE cci.chat_content_id IN (SELECT id FROM newest)
			AND LENGTH(TRIM(COALESCE(cci.html_s3_key, ''))) > 0
		ORDER BY cci.slide_number ASC
	`, chatID, db.ChatContentRoleAssistant).Scan(&htmlKeys).Error
	if err != nil {
		return nil, err
	}
	if len(htmlKeys) == 0 {
		return nil, nil
	}
	return htmlKeys, nil
}

// ListImagesForContent returns images for a single assistant (or any) content row in the chat.
func (r *Repository) ListImagesForContent(ctx context.Context, chatID, contentID uuid.UUID) ([]db.ChatContentImage, error) {
	var imgs []db.ChatContentImage
	err := r.db.WithContext(ctx).
		Joins("JOIN chat_content ON chat_content.id = chat_content_image.chat_content_id").
		Where("chat_content_image.chat_content_id = ? AND chat_content.chat_id = ?", contentID, chatID).
		Order("chat_content_image.slide_number ASC").
		Find(&imgs).Error
	return imgs, err
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

// CreateUserMessageAndJob inserts the user message row and a job (caller sets status, e.g. processing) in one transaction.
// When setTitle is non-empty, updates the chat title only if it is still unset (NULL or blank).
func (r *Repository) CreateUserMessageAndJob(ctx context.Context, userContent *db.ChatContent, job *db.Job, setTitle *string, attachments []db.ChatContentAttachment) error {
	return r.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		if err := tx.Create(userContent).Error; err != nil {
			return err
		}
		if len(attachments) > 0 {
			for i := range attachments {
				attachments[i].ChatContentID = userContent.ID
			}
			if err := tx.Create(&attachments).Error; err != nil {
				return err
			}
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
