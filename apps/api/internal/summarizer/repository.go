package summarizer

import (
	"context"
	"time"

	"content-creator-agent/internal/db"

	"github.com/google/uuid"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

// Repository runs DB queries for chat summarization.
type Repository struct {
	db *gorm.DB
}

// NewRepository constructs a summarizer repository.
func NewRepository(gdb *gorm.DB) *Repository {
	return &Repository{db: gdb}
}

// ListEligibleChatIDs returns chats that have never been summarized or have new content after the last summary.
func (r *Repository) ListEligibleChatIDs(ctx context.Context) ([]uuid.UUID, error) {
	var ids []uuid.UUID
	err := r.db.WithContext(ctx).Raw(`
SELECT DISTINCT cc.chat_id
FROM chat_content cc
LEFT JOIN chat_content_resume ccr ON ccr.chat_id = cc.chat_id
WHERE ccr.summarized_at IS NULL
   OR cc.created_at > ccr.summarized_at
`).Scan(&ids).Error
	return ids, err
}

// ListContentsOrdered returns chat messages in chronological order (same semantics as chat.Repository).
func (r *Repository) ListContentsOrdered(ctx context.Context, chatID uuid.UUID) ([]db.ChatContent, error) {
	var rows []db.ChatContent
	err := r.db.WithContext(ctx).
		Where("chat_id = ?", chatID).
		Order("created_at ASC").
		Find(&rows).Error
	return rows, err
}

// UpsertResume inserts or updates the resume row for a chat.
func (r *Repository) UpsertResume(ctx context.Context, chatID uuid.UUID, summary string, lastContentAt time.Time, summarizedAt time.Time) error {
	row := db.ChatContentResume{
		ID:            uuid.New(),
		ChatID:        chatID,
		Summary:       &summary,
		LastContentAt: &lastContentAt,
		SummarizedAt:  &summarizedAt,
	}
	return r.db.WithContext(ctx).Clauses(clause.OnConflict{
		Columns: []clause.Column{{Name: "chat_id"}},
		DoUpdates: clause.AssignmentColumns([]string{
			"summary", "last_content_at", "summarized_at", "updated_at",
		}),
	}).Create(&row).Error
}
