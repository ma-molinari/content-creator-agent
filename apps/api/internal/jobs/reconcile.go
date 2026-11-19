package jobs

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"strings"
	"time"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/storage"
	"github.com/google/uuid"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

type cleanupStorage interface {
	WalkObjectPages(context.Context, string, func([]storage.ObjectInfo) error) error
	DeleteMany(context.Context, []string) error
}

type cleanupInventory struct {
	ID         uuid.UUID
	ChatID     uuid.UUID
	ObjectKeys string
	JobIDs     string
	CreatedAt  time.Time
}

func (cleanupInventory) TableName() string { return "chat_cleanup_tasks" }

type reconcileStats struct {
	inventories, failedJobs, prefixes, pages, listedObjects, referenceQueries, deleteCalls, attemptedObjects int64
}

// ReconcileArtifacts sweeps old deleted-chat inventories and failed-job prefixes.
// Inventories remain as tombstones so uploads arriving late are removed on a later run.
func ReconcileArtifacts(ctx context.Context, gdb *gorm.DB, store cleanupStorage, cutoff time.Time) (result error) {
	started := time.Now()
	stats := &reconcileStats{}
	defer func() {
		outcome := "done"
		if result != nil {
			outcome = "failed"
		}
		log.Printf("[metrics] event=artifact_reconcile outcome=%s inventories=%d failed_jobs=%d prefixes=%d pages=%d listed_objects=%d reference_queries=%d delete_calls=%d attempted_objects=%d duration_ms=%d", outcome, stats.inventories, stats.failedJobs, stats.prefixes, stats.pages, stats.listedObjects, stats.referenceQueries, stats.deleteCalls, stats.attemptedObjects, time.Since(started).Milliseconds())
	}()
	const batchSize = 100
	var lastTaskTime time.Time
	var lastTaskID uuid.UUID
	for {
		var tasks []cleanupInventory
		query := gdb.WithContext(ctx).Where("created_at < ?", cutoff)
		if !lastTaskTime.IsZero() {
			query = query.Where("created_at > ? OR (created_at = ? AND id > ?)", lastTaskTime, lastTaskTime, lastTaskID)
		}
		if err := query.Order("created_at, id").Limit(batchSize).Find(&tasks).Error; err != nil {
			return err
		}
		// Bound each deletion batch while avoiding one S3 request per inventory.
		const maxDeleteBatch = 1000
		pending := make([]string, 0, maxDeleteBatch)
		var jobIDs []uuid.UUID
		flush := func() error {
			if err := deleteUnreferenced(ctx, gdb, store, pending, stats); err != nil {
				return err
			}
			pending = pending[:0]
			return nil
		}
		for _, task := range tasks {
			stats.inventories++
			var keys []string
			var ids []uuid.UUID
			if json.Unmarshal([]byte(task.ObjectKeys), &keys) != nil || json.Unmarshal([]byte(task.JobIDs), &ids) != nil {
				return errors.New("invalid cleanup inventory")
			}
			for len(keys) > 0 {
				size := maxDeleteBatch - len(pending)
				if size > len(keys) {
					size = len(keys)
				}
				pending = append(pending, keys[:size]...)
				keys = keys[size:]
				if len(pending) == maxDeleteBatch {
					if err := flush(); err != nil {
						return err
					}
				}
			}
			jobIDs = append(jobIDs, ids...)
		}
		if err := flush(); err != nil {
			return err
		}
		for _, id := range jobIDs {
			if err := reconcileJobPrefix(ctx, gdb, store, id, cutoff, stats); err != nil {
				return err
			}
		}
		if len(tasks) < batchSize {
			break
		}
		last := tasks[len(tasks)-1]
		lastTaskTime, lastTaskID = last.CreatedAt, last.ID
	}
	var lastJobTime time.Time
	var lastJobID uuid.UUID
	for {
		var failed []db.Job
		query := gdb.WithContext(ctx).Select("id", "updated_at").Where("status = ? AND updated_at < ?", db.JobStatusFailed, cutoff)
		if !lastJobTime.IsZero() {
			query = query.Where("updated_at > ? OR (updated_at = ? AND id > ?)", lastJobTime, lastJobTime, lastJobID)
		}
		if err := query.Order("updated_at, id").Limit(batchSize).Find(&failed).Error; err != nil {
			return err
		}
		for _, job := range failed {
			stats.failedJobs++
			if err := reconcileJobPrefix(ctx, gdb, store, job.ID, cutoff, stats); err != nil {
				return err
			}
		}
		if len(failed) < batchSize {
			break
		}
		last := failed[len(failed)-1]
		lastJobTime, lastJobID = last.UpdatedAt, last.ID
	}
	return nil
}

func reconcileJobPrefix(ctx context.Context, gdb *gorm.DB, store cleanupStorage, id uuid.UUID, cutoff time.Time, stats *reconcileStats) error {
	stats.prefixes++
	return gdb.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		var job db.Job
		err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&job, "id = ?", id).Error
		if err != nil && !errors.Is(err, gorm.ErrRecordNotFound) {
			return err
		}
		if err == nil && (job.Status != db.JobStatusFailed || !job.UpdatedAt.Before(cutoff)) {
			return nil
		}
		var versions int64
		if err := tx.Model(&db.PostVersion{}).Where("job_id = ?", id).Count(&versions).Error; err != nil {
			return err
		}
		if versions > 0 {
			return nil
		}
		prefix := fmt.Sprintf("slides/%s/", id)
		return store.WalkObjectPages(ctx, prefix, func(objects []storage.ObjectInfo) error {
			stats.pages++
			stats.listedObjects += int64(len(objects))
			keys := make([]string, 0, len(objects))
			for _, obj := range objects {
				if strings.HasPrefix(obj.Key, prefix) && obj.LastModified != nil && obj.LastModified.Before(cutoff) {
					keys = append(keys, obj.Key)
				}
			}
			return deleteUnreferenced(ctx, tx, store, keys, stats)
		})
	})
}

func deleteUnreferenced(ctx context.Context, gdb *gorm.DB, store cleanupStorage, keys []string, stats *reconcileStats) error {
	const maxLookupBatch = 500
	referenced := make(map[string]struct{})
	for start := 0; start < len(keys); start += maxLookupBatch {
		end := start + maxLookupBatch
		if end > len(keys) {
			end = len(keys)
		}
		batch := keys[start:end]
		var images []struct {
			S3Key     string
			HTMLS3Key *string
		}
		stats.referenceQueries++
		if err := gdb.WithContext(ctx).Table("chat_content_image").Select("s3_key", "html_s3_key").Where("s3_key IN ? OR html_s3_key IN ?", batch, batch).Scan(&images).Error; err != nil {
			return err
		}
		for _, image := range images {
			referenced[image.S3Key] = struct{}{}
			if image.HTMLS3Key != nil {
				referenced[*image.HTMLS3Key] = struct{}{}
			}
		}
		for _, table := range []struct{ name, column string }{
			{"chat_content_attachment", "s3_key"},
			{"post_versions", "document_s3_key"},
			{"user_profile_references", "s3_key"},
		} {
			var found []string
			stats.referenceQueries++
			if err := gdb.WithContext(ctx).Table(table.name).Where(table.column+" IN ?", batch).Pluck(table.column, &found).Error; err != nil {
				return err
			}
			for _, key := range found {
				referenced[key] = struct{}{}
			}
		}
	}
	safe := make([]string, 0, len(keys))
	seen := make(map[string]struct{})
	for _, key := range keys {
		if key == "" {
			continue
		}
		if _, ok := referenced[key]; ok {
			continue
		}
		if _, ok := seen[key]; ok {
			continue
		}
		seen[key] = struct{}{}
		safe = append(safe, key)
	}
	if len(safe) == 0 {
		return nil
	}
	stats.deleteCalls++
	stats.attemptedObjects += int64(len(safe))
	if err := store.DeleteMany(ctx, safe); err != nil {
		log.Printf("[metrics] event=artifact_cleanup outcome=failed objects=%d", len(safe))
		return err
	}
	log.Printf("[metrics] event=artifact_cleanup outcome=done objects=%d", len(safe))
	return nil
}
