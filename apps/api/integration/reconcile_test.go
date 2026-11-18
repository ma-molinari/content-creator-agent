//go:build integration

package integration

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"testing"
	"time"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"content-creator-agent/internal/storage"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

type reconcileStore struct {
	objects  map[string][]storage.ObjectInfo
	deleted  []string
	failNext bool
}

func (s *reconcileStore) ListObjects(_ context.Context, prefix string) ([]storage.ObjectInfo, error) {
	return s.objects[prefix], nil
}
func (s *reconcileStore) DeleteMany(_ context.Context, keys []string) error {
	if s.failNext {
		s.failNext = false
		return errors.New("temporary failure")
	}
	s.deleted = append(s.deleted, keys...)
	return nil
}

func TestReconcileProtectsActiveRecentAndReferencedObjects(t *testing.T) {
	env := newTestEnv(t, nil)
	userID, chatID := uuid.New(), uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: userID, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", userID) })
	require.NoError(t, env.DB.Create(&db.Chat{ID: chatID, UserID: userID, PostType: db.PostTypeSingle}).Error)
	failedID, activeID, doneID, deletedID := uuid.New(), uuid.New(), uuid.New(), uuid.New()
	old := time.Now().Add(-48 * time.Hour)
	cutoff := time.Now().Add(-24 * time.Hour)
	recent := time.Now()
	for _, entry := range []struct {
		id     uuid.UUID
		status db.JobStatus
	}{{failedID, db.JobStatusFailed}, {activeID, db.JobStatusProcessing}, {doneID, db.JobStatusDone}} {
		require.NoError(t, env.DB.Create(&db.Job{ID: entry.id, ChatID: chatID, UserID: userID, Status: entry.status, UpdatedAt: old}).Error)
	}
	prefix := func(id uuid.UUID) string { return fmt.Sprintf("slides/%s/", id) }
	refKey := "users/reference.jpg"
	require.NoError(t, env.DB.Create(&db.UserProfileReference{ID: uuid.New(), UserID: userID, S3Key: refKey}).Error)
	keys, _ := json.Marshal([]string{refKey, "users/deleted.jpg"})
	ids, _ := json.Marshal([]uuid.UUID{deletedID})
	taskID := uuid.New()
	require.NoError(t, env.DB.Exec("INSERT INTO chat_cleanup_tasks (id,chat_id,object_keys,job_ids,created_at) VALUES (?,?,?,?,?)", taskID, uuid.New(), string(keys), string(ids), old).Error)
	t.Cleanup(func() { env.DB.Exec("DELETE FROM chat_cleanup_tasks WHERE id = ?", taskID) })
	store := &reconcileStore{objects: map[string][]storage.ObjectInfo{
		prefix(failedID):  {{Key: prefix(failedID) + "old.jpeg", LastModified: &old}, {Key: prefix(failedID) + "recent.jpeg", LastModified: &recent}, {Key: prefix(failedID) + "unknown.jpeg"}},
		prefix(activeID):  {{Key: prefix(activeID) + "active.jpeg", LastModified: &old}},
		prefix(doneID):    {{Key: prefix(doneID) + "done.jpeg", LastModified: &old}},
		prefix(deletedID): {{Key: prefix(deletedID) + "orphan.html", LastModified: &old}},
	}}
	store.failNext = true
	require.Error(t, jobs.ReconcileArtifacts(context.Background(), env.DB, store, cutoff))
	require.Empty(t, store.deleted)
	require.NoError(t, jobs.ReconcileArtifacts(context.Background(), env.DB, store, cutoff))
	require.ElementsMatch(t, []string{"users/deleted.jpg", prefix(failedID) + "old.jpeg", prefix(deletedID) + "orphan.html"}, store.deleted)
	store.deleted = nil
	require.NoError(t, jobs.ReconcileArtifacts(context.Background(), env.DB, store, cutoff))
	require.ElementsMatch(t, []string{"users/deleted.jpg", prefix(failedID) + "old.jpeg", prefix(deletedID) + "orphan.html"}, store.deleted)
}

func TestReconcilePaginatesInventoriesWithEqualTimestamps(t *testing.T) {
	env := newTestEnv(t, nil)
	old := time.Now().UTC().Add(-48 * time.Hour).Truncate(time.Second)
	cutoff := time.Now().UTC().Add(-24 * time.Hour)
	ids := make([]uuid.UUID, 0, 205)
	expected := make([]string, 0, 205)
	t.Cleanup(func() { env.DB.Exec("DELETE FROM chat_cleanup_tasks WHERE id IN ?", ids) })
	for i := 0; i < 205; i++ {
		id := uuid.New()
		ids = append(ids, id)
		key := "users/pagination/" + id.String()
		expected = append(expected, key)
		keys, err := json.Marshal([]string{key})
		require.NoError(t, err)
		require.NoError(t, env.DB.Exec("INSERT INTO chat_cleanup_tasks (id,chat_id,object_keys,job_ids,created_at) VALUES (?,?,?,?,?)", id, uuid.New(), string(keys), "[]", old).Error)
	}
	store := &reconcileStore{objects: map[string][]storage.ObjectInfo{}}
	require.NoError(t, jobs.ReconcileArtifacts(context.Background(), env.DB, store, cutoff))
	require.ElementsMatch(t, expected, store.deleted)
}

func TestReconcilePaginatesFailedJobsWithEqualTimestamps(t *testing.T) {
	env := newTestEnv(t, nil)
	userID, chatID := uuid.New(), uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: userID, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", userID) })
	require.NoError(t, env.DB.Create(&db.Chat{ID: chatID, UserID: userID, PostType: db.PostTypeSingle}).Error)
	old := time.Now().UTC().Add(-48 * time.Hour).Truncate(time.Second)
	cutoff := time.Now().UTC().Add(-24 * time.Hour)
	store := &reconcileStore{objects: map[string][]storage.ObjectInfo{}}
	expected := make([]string, 0, 105)
	for i := 0; i < 105; i++ {
		id := uuid.New()
		require.NoError(t, env.DB.Create(&db.Job{ID: id, ChatID: chatID, UserID: userID, Status: db.JobStatusFailed, UpdatedAt: old}).Error)
		prefix := fmt.Sprintf("slides/%s/", id)
		key := prefix + "document.json"
		expected = append(expected, key)
		store.objects[prefix] = []storage.ObjectInfo{{Key: key, LastModified: &old}}
	}
	require.NoError(t, jobs.ReconcileArtifacts(context.Background(), env.DB, store, cutoff))
	require.ElementsMatch(t, expected, store.deleted)
}
