package jobs

import (
	"context"
	"encoding/json"
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

type cleanupStorage interface {
	ListObjects(context.Context, string) ([]storage.ObjectInfo, error)
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

// ReconcileArtifacts sweeps old deleted-chat inventories and failed-job prefixes.
// Inventories remain as tombstones so uploads arriving late are removed on a later run.
func ReconcileArtifacts(ctx context.Context, gdb *gorm.DB, store cleanupStorage, cutoff time.Time) error {
	var tasks []cleanupInventory
	if err := gdb.WithContext(ctx).Where("created_at < ?", cutoff).Find(&tasks).Error; err != nil {
		return err
	}
	for _, task := range tasks {
		var keys []string
		var ids []uuid.UUID
		if json.Unmarshal([]byte(task.ObjectKeys), &keys) != nil || json.Unmarshal([]byte(task.JobIDs), &ids) != nil {
			return errors.New("invalid cleanup inventory")
		}
		if err := deleteUnreferenced(ctx, gdb, store, keys); err != nil {
			return err
		}
		for _, id := range ids {
			if err := reconcileJobPrefix(ctx, gdb, store, id, cutoff); err != nil {
				return err
			}
		}
	}
	var failed []db.Job
	if err := gdb.WithContext(ctx).Select("id").Where("status = ? AND updated_at < ?", db.JobStatusFailed, cutoff).Find(&failed).Error; err != nil {
		return err
	}
	for _, job := range failed {
		if err := reconcileJobPrefix(ctx, gdb, store, job.ID, cutoff); err != nil {
			return err
		}
	}
	return nil
}

func reconcileJobPrefix(ctx context.Context, gdb *gorm.DB, store cleanupStorage, id uuid.UUID, cutoff time.Time) error {
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
		objects, err := store.ListObjects(ctx, prefix)
		if err != nil {
			return err
		}
		keys := make([]string, 0, len(objects))
		for _, obj := range objects {
			if strings.HasPrefix(obj.Key, prefix) && obj.LastModified != nil && obj.LastModified.Before(cutoff) {
				keys = append(keys, obj.Key)
			}
		}
		return deleteUnreferenced(ctx, tx, store, keys)
	})
}

func deleteUnreferenced(ctx context.Context, gdb *gorm.DB, store cleanupStorage, keys []string) error {
	safe := make([]string, 0, len(keys))
	for _, key := range keys {
		if key == "" {
			continue
		}
		var n int64
		for _, query := range []struct{ table, condition string }{
			{"chat_content_image", "s3_key = ? OR html_s3_key = ?"},
			{"chat_content_attachment", "s3_key = ? OR s3_key = ?"},
			{"post_versions", "document_s3_key = ? OR document_s3_key = ?"},
			{"user_profile_references", "s3_key = ? OR s3_key = ?"},
		} {
			if err := gdb.WithContext(ctx).Table(query.table).Where(query.condition, key, key).Count(&n).Error; err != nil {
				return err
			}
			if n > 0 {
				break
			}
		}
		if n == 0 {
			safe = append(safe, key)
		}
	}
	if len(safe) == 0 {
		return nil
	}
	return store.DeleteMany(ctx, safe)
}
