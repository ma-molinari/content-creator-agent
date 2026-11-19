package jobs

import (
	"context"
	"fmt"
	"log"
	"regexp"
	"time"

	"content-creator-agent/internal/db"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

var safeMetricCode = regexp.MustCompile(`^[A-Za-z0-9_]{1,64}$`)
var safeMetricVersion = regexp.MustCompile(`^[A-Za-z0-9._-]{1,64}$`)

func metricErrorCode(value *string) string {
	if value != nil && safeMetricCode.MatchString(*value) {
		return *value
	}
	return "UNSPECIFIED"
}

// logJobOutcome emits countable, content-free events for a terminal transition.
func logJobOutcome(ctx context.Context, gdb *gorm.DB, jobID uuid.UUID, outcome, code string) {
	var job db.Job
	if err := gdb.WithContext(ctx).Select("id", "chat_id", "stage", "post_format", "created_at").First(&job, "id = ?", jobID).Error; err != nil {
		return
	}
	var version *db.PostVersion
	if job.PostFormat == db.PostFormatStructuredV1 && outcome == "done" {
		var found db.PostVersion
		if result := gdb.WithContext(ctx).Model(&db.PostVersion{}).Select("schema_version", "renderer_version").Where("job_id = ?", jobID).Scan(&found); result.Error == nil && result.RowsAffected == 1 {
			version = &found
		}
	}
	logTerminalJob(job, outcome, code, version)
}

func logTerminalJob(job db.Job, outcome, code string, version *db.PostVersion) {
	elapsed := time.Since(job.CreatedAt).Milliseconds()
	if elapsed < 0 {
		elapsed = 0
	}
	schema, renderer := "unknown", "unknown"
	if version != nil && version.SchemaVersion > 0 && safeMetricVersion.MatchString(version.RendererVersion) {
		schema = fmt.Sprint(version.SchemaVersion)
		renderer = version.RendererVersion
	}
	log.Printf("[metrics] event=job_terminal job_id=%s chat_id=%s stage=%s format=%s schema_version=%s renderer_version=%s outcome=%s code=%s duration_ms=%d", job.ID, job.ChatID, metricErrorCode(&job.Stage), job.PostFormat, schema, renderer, outcome, code, elapsed)
}
