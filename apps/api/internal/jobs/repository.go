package jobs

import (
	"context"
	"time"

	"content-creator-agent/internal/db"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// Repository persists job rows.
type Repository struct {
	db *gorm.DB
}

// NewRepository constructs a jobs repository.
func NewRepository(gdb *gorm.DB) *Repository {
	return &Repository{db: gdb}
}

// GetByID loads a job by primary key.
func (r *Repository) GetByID(ctx context.Context, id uuid.UUID) (*db.Job, error) {
	var j db.Job
	err := r.db.WithContext(ctx).First(&j, "id = ?", id).Error
	if err != nil {
		return nil, err
	}
	return &j, nil
}

// UpdateStatus sets job status and optional error message.
func (r *Repository) UpdateStatus(ctx context.Context, id uuid.UUID, status db.JobStatus, errMsg *string) error {
	updates := map[string]interface{}{
		"status":     status,
		"updated_at": time.Now().UTC(),
	}
	if errMsg != nil {
		updates["error_msg"] = *errMsg
	} else {
		updates["error_msg"] = nil
	}
	return r.db.WithContext(ctx).Model(&db.Job{}).Where("id = ?", id).Updates(updates).Error
}

// FailStuckProcessingJobs marks processing jobs older than cutoff as failed.
func (r *Repository) FailStuckProcessingJobs(ctx context.Context, cutoff time.Time, errMsg string) (int64, error) {
	res := r.db.WithContext(ctx).Model(&db.Job{}).
		Where("status = ? AND updated_at < ?", db.JobStatusProcessing, cutoff).
		Updates(map[string]interface{}{
			"status":     db.JobStatusFailed,
			"error_msg":  errMsg,
			"updated_at": time.Now().UTC(),
		})
	return res.RowsAffected, res.Error
}
