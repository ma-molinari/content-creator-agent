package profile

import (
	"context"
	"errors"

	"content-creator-agent/internal/db"

	"github.com/google/uuid"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

// Repository persists user profile audit/brand text.
type Repository struct {
	db *gorm.DB
}

// NewRepository constructs a profile repository.
func NewRepository(gdb *gorm.DB) *Repository {
	return &Repository{db: gdb}
}

// GetByUserID returns the row for userID, or (nil, nil) if none.
func (r *Repository) GetByUserID(ctx context.Context, userID uuid.UUID) (*db.UserProfile, error) {
	var p db.UserProfile
	err := r.db.WithContext(ctx).Where("user_id = ?", userID).First(&p).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &p, nil
}

// Upsert inserts or updates audit and brand text for the user.
func (r *Repository) Upsert(ctx context.Context, userID uuid.UUID, auditText, brandText string) error {
	row := db.UserProfile{
		ID:        uuid.New(),
		UserID:    userID,
		AuditText: auditText,
		BrandText: brandText,
	}
	return r.db.WithContext(ctx).Clauses(clause.OnConflict{
		Columns: []clause.Column{{Name: "user_id"}},
		DoUpdates: clause.AssignmentColumns([]string{"audit_text", "brand_text", "updated_at"}),
	}).Create(&row).Error
}
