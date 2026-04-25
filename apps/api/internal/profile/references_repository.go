package profile

import (
	"context"
	"errors"

	"content-creator-agent/internal/db"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// ReferencesRepository persists design reference images metadata (S3 keys per user).
type ReferencesRepository struct {
	db *gorm.DB
}

// NewReferencesRepository constructs a references repository.
func NewReferencesRepository(gdb *gorm.DB) *ReferencesRepository {
	return &ReferencesRepository{db: gdb}
}

// ListByUserID returns rows ordered for display and worker consumption.
func (r *ReferencesRepository) ListByUserID(ctx context.Context, userID uuid.UUID) ([]db.UserProfileReference, error) {
	var rows []db.UserProfileReference
	err := r.db.WithContext(ctx).Where("user_id = ?", userID).
		Order("sort_order ASC, created_at ASC").Find(&rows).Error
	return rows, err
}

// ListS3KeysByUserID returns S3 object keys in display order.
func (r *ReferencesRepository) ListS3KeysByUserID(ctx context.Context, userID uuid.UUID) ([]string, error) {
	rows, err := r.ListByUserID(ctx, userID)
	if err != nil {
		return nil, err
	}
	out := make([]string, 0, len(rows))
	for _, row := range rows {
		out = append(out, row.S3Key)
	}
	return out, nil
}

// CountByUserID returns how many reference rows exist for the user.
func (r *ReferencesRepository) CountByUserID(ctx context.Context, userID uuid.UUID) (int64, error) {
	var n int64
	err := r.db.WithContext(ctx).Model(&db.UserProfileReference{}).Where("user_id = ?", userID).Count(&n).Error
	return n, err
}

// Create inserts a new reference with the next sort_order.
func (r *ReferencesRepository) Create(ctx context.Context, userID uuid.UUID, s3Key string) (*db.UserProfileReference, error) {
	var maxOrder int
	err := r.db.WithContext(ctx).Raw(
		`SELECT COALESCE(MAX(sort_order), -1) FROM user_profile_references WHERE user_id = ?`,
		userID,
	).Scan(&maxOrder).Error
	if err != nil {
		return nil, err
	}
	row := &db.UserProfileReference{
		ID:        uuid.New(),
		UserID:    userID,
		S3Key:     s3Key,
		SortOrder: maxOrder + 1,
	}
	if err := r.db.WithContext(ctx).Create(row).Error; err != nil {
		return nil, err
	}
	return row, nil
}

// GetByIDForUser returns the row if it exists and belongs to the user.
func (r *ReferencesRepository) GetByIDForUser(ctx context.Context, id, userID uuid.UUID) (*db.UserProfileReference, error) {
	var row db.UserProfileReference
	err := r.db.WithContext(ctx).Where("id = ? AND user_id = ?", id, userID).First(&row).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &row, nil
}

// DeleteByIDForUser removes the row; caller deletes S3 object.
func (r *ReferencesRepository) DeleteByIDForUser(ctx context.Context, id, userID uuid.UUID) error {
	res := r.db.WithContext(ctx).Where("id = ? AND user_id = ?", id, userID).Delete(&db.UserProfileReference{})
	if res.Error != nil {
		return res.Error
	}
	if res.RowsAffected == 0 {
		return gorm.ErrRecordNotFound
	}
	return nil
}
