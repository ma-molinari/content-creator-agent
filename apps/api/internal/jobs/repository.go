package jobs

import (
	"context"
	"strings"
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

// UpdateStatus sets job status and optional error message.
func (r *Repository) UpdateStatus(ctx context.Context, id uuid.UUID, status db.JobStatus, errMsg *string) error {
	stage := string(status)
	progress := 0
	if status == db.JobStatusDone || status == db.JobStatusFailed {
		progress = 100
	}
	updates := map[string]interface{}{
		"status":     status,
		"stage":      stage,
		"progress":   progress,
		"updated_at": time.Now().UTC(),
	}
	if errMsg != nil {
		updates["error_msg"] = *errMsg
	} else {
		updates["error_msg"] = nil
	}
	return r.db.WithContext(ctx).Model(&db.Job{}).Where("id = ?", id).Updates(updates).Error
}

// FailIfActive cannot overwrite a terminal callback that raced with dispatch.
func (r *Repository) FailIfActive(ctx context.Context, id uuid.UUID, msg string) (bool, error) {
	res := r.db.WithContext(ctx).Model(&db.Job{}).
		Where("id = ? AND status IN ?", id, []db.JobStatus{db.JobStatusPending, db.JobStatusProcessing}).
		Updates(map[string]interface{}{"status": db.JobStatusFailed, "stage": "failed", "progress": 100,
			"error_msg": msg, "error_code": "dispatch_failed", "updated_at": time.Now().UTC()})
	if res.Error == nil && res.RowsAffected > 0 {
		logJobOutcome(ctx, r.db, id, "failed", "DISPATCH_FAILED")
	}
	return res.RowsAffected > 0, res.Error
}

// UpdateProgress records worker stage/progress and refreshes the job heartbeat.
func (r *Repository) UpdateProgress(ctx context.Context, id uuid.UUID, stage string, progress int, errorCode *string) error {
	stage = strings.TrimSpace(stage)
	if stage == "" {
		stage = "processing"
	}
	if progress < 0 {
		progress = 0
	}
	if progress > 100 {
		progress = 100
	}
	now := time.Now().UTC()
	updates := map[string]interface{}{
		"stage":        stage,
		"progress":     gorm.Expr("CASE WHEN progress > ? THEN progress ELSE ? END", progress, progress),
		"heartbeat_at": now,
		"updated_at":   now,
	}
	if errorCode != nil {
		code := strings.TrimSpace(*errorCode)
		if code == "" {
			updates["error_code"] = nil
		} else {
			updates["error_code"] = code
		}
	}
	return r.db.WithContext(ctx).Model(&db.Job{}).
		Where("id = ? AND status = ?", id, db.JobStatusProcessing).
		Updates(updates).Error
}

// FailStuckProcessingJobs marks processing jobs older than cutoff as failed.
func (r *Repository) FailStuckProcessingJobs(ctx context.Context, cutoff time.Time, errMsg string) (int64, error) {
	res := r.db.WithContext(ctx).Model(&db.Job{}).
		Where("status = ? AND COALESCE(heartbeat_at, updated_at) < ?", db.JobStatusProcessing, cutoff).
		Updates(map[string]interface{}{
			"status":     db.JobStatusFailed,
			"stage":      "failed",
			"progress":   100,
			"error_msg":  errMsg,
			"error_code": "stuck_processing",
			"updated_at": time.Now().UTC(),
		})
	return res.RowsAffected, res.Error
}
