//go:build integration

package integration

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"strings"
	"testing"
	"time"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"content-creator-agent/internal/storage"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

type reconcileStore struct {
	objects      map[string][]storage.ObjectInfo
	deleted      []string
	failNext     bool
	pageSize     int
	deleteCalls  int
	failOnDelete int
}

func (s *reconcileStore) WalkObjectPages(_ context.Context, prefix string, visit func([]storage.ObjectInfo) error) error {
	objects := s.objects[prefix]
	pageSize := s.pageSize
	if pageSize == 0 {
		pageSize = 1000
	}
	for start := 0; start < len(objects); start += pageSize {
		end := start + pageSize
		if end > len(objects) {
			end = len(objects)
		}
		if err := visit(objects[start:end]); err != nil {
			return err
		}
	}
	return nil
}
func (s *reconcileStore) DeleteMany(_ context.Context, keys []string) error {
	s.deleteCalls++
	if s.failOnDelete == s.deleteCalls {
		return errors.New("temporary page failure")
	}
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
	contentID := uuid.New()
	require.NoError(t, env.DB.Create(&db.ChatContent{ID: contentID, ChatID: chatID, Role: db.ChatContentRoleAssistant, Content: "ok"}).Error)
	imageKey, htmlKey, attachmentKey, documentKey := "slides/protected.jpeg", "slides/protected.html", "users/attachment.png", "slides/protected.json"
	require.NoError(t, env.DB.Create(&db.ChatContentImage{ID: uuid.New(), ChatContentID: contentID, S3Key: imageKey, HtmlS3Key: &htmlKey, URL: "url", SlideNumber: 1}).Error)
	require.NoError(t, env.DB.Create(&db.ChatContentAttachment{ID: uuid.New(), ChatContentID: contentID, S3Key: attachmentKey, MimeType: "image/png", SizeBytes: 1}).Error)
	require.NoError(t, env.DB.Create(&db.PostVersion{ID: uuid.New(), ChatID: chatID, JobID: doneID, AssistantContentID: contentID, DocumentS3Key: documentKey, SchemaVersion: 1, RendererVersion: "1"}).Error)
	keys, _ := json.Marshal([]string{refKey, imageKey, htmlKey, attachmentKey, documentKey, "users/deleted.jpg"})
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
	original := log.Writer()
	var output bytes.Buffer
	log.SetOutput(&output)
	t.Cleanup(func() { log.SetOutput(original) })
	store.failNext = true
	require.Error(t, jobs.ReconcileArtifacts(context.Background(), env.DB, store, cutoff))
	require.Empty(t, store.deleted)
	require.NoError(t, jobs.ReconcileArtifacts(context.Background(), env.DB, store, cutoff))
	require.ElementsMatch(t, []string{"users/deleted.jpg", prefix(failedID) + "old.jpeg", prefix(deletedID) + "orphan.html"}, store.deleted)
	store.deleted = nil
	require.NoError(t, jobs.ReconcileArtifacts(context.Background(), env.DB, store, cutoff))
	require.ElementsMatch(t, []string{"users/deleted.jpg", prefix(failedID) + "old.jpeg", prefix(deletedID) + "orphan.html"}, store.deleted)
	require.Equal(t, 1, strings.Count(output.String(), "event=artifact_reconcile outcome=failed"))
	require.Equal(t, 2, strings.Count(output.String(), "event=artifact_reconcile outcome=done"))
	require.Contains(t, output.String(), "inventories=1")
	require.Contains(t, output.String(), "reference_queries=")
	require.Contains(t, output.String(), "duration_ms=")
	require.NotContains(t, output.String(), refKey)
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
	require.Equal(t, 3, store.deleteCalls)
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

func TestReconcileRetriesAfterObjectPageFailure(t *testing.T) {
	env := newTestEnv(t, nil)
	userID, chatID, jobID := uuid.New(), uuid.New(), uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: userID, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", userID) })
	require.NoError(t, env.DB.Create(&db.Chat{ID: chatID, UserID: userID, PostType: db.PostTypeSingle}).Error)
	old := time.Now().UTC().Add(-48 * time.Hour)
	cutoff := time.Now().UTC().Add(-24 * time.Hour)
	require.NoError(t, env.DB.Create(&db.Job{ID: jobID, ChatID: chatID, UserID: userID, Status: db.JobStatusFailed, UpdatedAt: old}).Error)
	prefix := fmt.Sprintf("slides/%s/", jobID)
	keys := []string{prefix + "one", prefix + "two", prefix + "three"}
	store := &reconcileStore{pageSize: 1, failOnDelete: 2, objects: map[string][]storage.ObjectInfo{prefix: {
		{Key: keys[0], LastModified: &old}, {Key: keys[1], LastModified: &old}, {Key: keys[2], LastModified: &old},
	}}}
	require.Error(t, jobs.ReconcileArtifacts(context.Background(), env.DB, store, cutoff))
	require.Equal(t, keys[:1], store.deleted)
	store.deleted = nil
	require.NoError(t, jobs.ReconcileArtifacts(context.Background(), env.DB, store, cutoff))
	require.ElementsMatch(t, keys, store.deleted)
}

func TestReconcileLargeInventoryProtectsReferencesAcrossBatches(t *testing.T) {
	env := newTestEnv(t, nil)
	uid, taskID := uuid.New(), uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: uid, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() {
		env.DB.Delete(&db.User{}, "id = ?", uid)
		env.DB.Exec("DELETE FROM chat_cleanup_tasks WHERE id = ?", taskID)
	})
	keys := make([]string, 0, 1002)
	for i := 0; i < 1001; i++ {
		keys = append(keys, fmt.Sprintf("users/large/%04d", i))
	}
	referenced := keys[900]
	require.NoError(t, env.DB.Create(&db.UserProfileReference{ID: uuid.New(), UserID: uid, S3Key: referenced}).Error)
	keys = append(keys, keys[0])
	encoded, err := json.Marshal(keys)
	require.NoError(t, err)
	old := time.Now().UTC().Add(-48 * time.Hour)
	require.NoError(t, env.DB.Exec("INSERT INTO chat_cleanup_tasks (id,chat_id,object_keys,job_ids,created_at) VALUES (?,?,?,?,?)", taskID, uuid.New(), string(encoded), "[]", old).Error)
	store := &reconcileStore{objects: map[string][]storage.ObjectInfo{}}
	require.NoError(t, jobs.ReconcileArtifacts(context.Background(), env.DB, store, time.Now().UTC().Add(-24*time.Hour)))
	require.NotContains(t, store.deleted, referenced)
	require.Len(t, store.deleted, 1001)
	require.Equal(t, 2, store.deleteCalls)
}
