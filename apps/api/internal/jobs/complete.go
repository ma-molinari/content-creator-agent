package jobs

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/storage"

	"github.com/google/uuid"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

const signedURLExpiry = time.Hour

// StuckJobErrorMsg is persisted when a job stays in processing longer than the configured threshold.
const StuckJobErrorMsg = "processing timed out (worker did not complete in time)"

var (
	// ErrJobCompleteConflict means the job already failed and cannot accept a success callback.
	ErrJobCompleteConflict = errors.New("jobs: cannot complete a failed job")
	// ErrJobNotProcessing means the job is not in processing state for a success completion.
	ErrJobNotProcessing = errors.New("jobs: job is not in processing state")
	// ErrArtifactObjectNotFound means HeadObject failed for a declared JPEG/HTML key before persisting DB rows.
	ErrArtifactObjectNotFound = errors.New("jobs: slide artifact object not found in storage")
)

// ArtifactRef is an S3 object produced by the worker for one slide.
type ArtifactRef struct {
	S3Key       string
	SlideNumber int
	HtmlS3Key   *string // optional HTML source key under slides/{jobID}/
}

func ensureSlideArtifactsExist(ctx context.Context, jobID uuid.UUID, artifacts []ArtifactRef, store storage.StorageService) error {
	for _, a := range artifacts {
		key := strings.TrimSpace(a.S3Key)
		if key == "" {
			return gorm.ErrInvalidData
		}
		if e := validateSlideArtifactKey(jobID, key); e != nil {
			return e
		}
		if e := store.HeadObject(ctx, key); e != nil {
			if storage.IsObjectNotFound(e) {
				return ErrArtifactObjectNotFound
			}
			return e
		}
		if a.HtmlS3Key != nil {
			hk := strings.TrimSpace(*a.HtmlS3Key)
			if hk != "" {
				if e := validateSlideArtifactKey(jobID, hk); e != nil {
					return e
				}
				if e := store.HeadObject(ctx, hk); e != nil {
					if storage.IsObjectNotFound(e) {
						return ErrArtifactObjectNotFound
					}
					return e
				}
			}
		}
	}
	return nil
}

// CompleteAssistantReply persists the assistant message, slide images, and marks the job done.
// If the job is already done, it returns alreadyDone=true and no error (idempotent).
// If the job is failed, it returns ErrJobCompleteConflict.
func CompleteAssistantReply(ctx context.Context, gdb *gorm.DB, jobID uuid.UUID, assistantText string, artifacts []ArtifactRef, store storage.StorageService) (alreadyDone bool, err error) {
	err = gdb.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		var job db.Job
		if e := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&job, "id = ?", jobID).Error; e != nil {
			return e
		}
		switch job.Status {
		case db.JobStatusDone:
			alreadyDone = true
			return nil
		case db.JobStatusFailed:
			return ErrJobCompleteConflict
		case db.JobStatusProcessing:
			if e := ensureSlideArtifactsExist(ctx, job.ID, artifacts, store); e != nil {
				return e
			}
		default:
			return ErrJobNotProcessing
		}

		asst := &db.ChatContent{
			ID:      uuid.New(),
			ChatID:  job.ChatID,
			Role:    db.ChatContentRoleAssistant,
			Content: assistantText,
		}
		if e := tx.Create(asst).Error; e != nil {
			return e
		}
		for _, a := range artifacts {
			key := strings.TrimSpace(a.S3Key)
			if key == "" {
				return gorm.ErrInvalidData
			}
			if e := validateSlideArtifactKey(job.ID, key); e != nil {
				return e
			}
			url, e := store.GetSignedURL(ctx, key, signedURLExpiry)
			if e != nil {
				return e
			}
			img := db.ChatContentImage{
				ID:            uuid.New(),
				ChatContentID: asst.ID,
				S3Key:         key,
				URL:           url,
				SlideNumber:   a.SlideNumber,
			}
			if a.HtmlS3Key != nil {
				hk := strings.TrimSpace(*a.HtmlS3Key)
				if hk != "" {
					if e := validateSlideArtifactKey(job.ID, hk); e != nil {
						return e
					}
					img.HtmlS3Key = &hk
				}
			}
			if e := tx.Create(&img).Error; e != nil {
				return e
			}
		}
		now := time.Now().UTC()
		return tx.Model(&db.Job{}).Where("id = ?", job.ID).Updates(map[string]interface{}{
			"status":     db.JobStatusDone,
			"error_msg":  nil,
			"updated_at": now,
		}).Error
	})
	return alreadyDone, err
}

// ApplyWorkerFailure marks the job failed when the worker reports an error.
// Returns noop=true if the job was already terminal (done or failed), so the HTTP layer can return 204 without changing state.
func ApplyWorkerFailure(ctx context.Context, gdb *gorm.DB, jobID uuid.UUID, workerErr string) (noop bool, err error) {
	msg := strings.TrimSpace(workerErr)
	err = gdb.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		var job db.Job
		if e := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&job, "id = ?", jobID).Error; e != nil {
			return e
		}
		switch job.Status {
		case db.JobStatusDone, db.JobStatusFailed:
			noop = true
			return nil
		case db.JobStatusProcessing, db.JobStatusPending:
			now := time.Now().UTC()
			return tx.Model(&db.Job{}).Where("id = ?", job.ID).Updates(map[string]interface{}{
				"status":     db.JobStatusFailed,
				"error_msg":  msg,
				"updated_at": now,
			}).Error
		}
		return fmt.Errorf("jobs: unexpected job status %q", job.Status)
	})
	return noop, err
}
