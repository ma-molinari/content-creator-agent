package profile

import (
	"context"
	"errors"
	"fmt"
	"regexp"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/storage"

	"gorm.io/gorm"
)

var retiredReferenceName = regexp.MustCompile(`^[0-9a-fA-F-]{36}\.(jpg|png|webp|gif)$`)

// RetireReferences deletes only registered profile reference sources. Run with all
// old API instances stopped so no new job can start using a reference concurrently.
// Delete S3 first; an interrupted run can safely retry the remaining database row.
func RetireReferences(ctx context.Context, database *gorm.DB, store storage.StorageService) (int, error) {
	if database == nil || store == nil {
		return 0, errors.New("profile: database and storage are required")
	}
	var active int64
	if err := database.WithContext(ctx).Model(&db.Job{}).Where("status IN ?", []db.JobStatus{db.JobStatusPending, db.JobStatusProcessing}).Count(&active).Error; err != nil {
		return 0, err
	}
	if active != 0 {
		return 0, errors.New("profile: active jobs must finish before removing references")
	}
	var rows []db.UserProfileReference
	if err := database.WithContext(ctx).Order("created_at, id").Find(&rows).Error; err != nil {
		return 0, err
	}
	removed := 0
	for _, row := range rows {
		prefix := fmt.Sprintf("users/%s/design-refs/", row.UserID.String())
		if len(row.S3Key) <= len(prefix) || row.S3Key[:len(prefix)] != prefix || !retiredReferenceName.MatchString(row.S3Key[len(prefix):]) {
			return removed, errors.New("profile: invalid reference key; cleanup stopped")
		}
		if err := store.Delete(ctx, row.S3Key); err != nil {
			return removed, err
		}
		result := database.WithContext(ctx).Where("id = ? AND user_id = ? AND s3_key = ?", row.ID, row.UserID, row.S3Key).Delete(&db.UserProfileReference{})
		if result.Error != nil {
			return removed, result.Error
		}
		if result.RowsAffected != 1 {
			return removed, errors.New("profile: reference changed during cleanup")
		}
		removed++
	}
	return removed, nil
}
