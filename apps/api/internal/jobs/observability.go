package jobs

import (
	"context"
	"log"
	"regexp"
	"time"

	"content-creator-agent/internal/db"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

var safeMetricCode = regexp.MustCompile(`^[A-Z0-9_]{1,64}$`)

func metricErrorCode(value *string) string {
	if value != nil && safeMetricCode.MatchString(*value) {
		return *value
	}
	return "UNSPECIFIED"
}

// logJobOutcome emits countable, content-free events for a terminal transition.
func logJobOutcome(ctx context.Context, gdb *gorm.DB, jobID uuid.UUID, outcome, code string) {
	var job db.Job
	if err := gdb.WithContext(ctx).Select("id", "post_format", "created_at").First(&job, "id = ?", jobID).Error; err != nil {
		return
	}
	elapsed := time.Since(job.CreatedAt).Milliseconds()
	if elapsed < 0 {
		elapsed = 0
	}
	log.Printf("[metrics] event=job_terminal job_id=%s format=%s outcome=%s code=%s duration_ms=%d", jobID, job.PostFormat, outcome, code, elapsed)
}
