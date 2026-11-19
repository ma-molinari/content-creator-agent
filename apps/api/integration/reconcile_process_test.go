//go:build integration

package integration

import (
	"context"
	"errors"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"content-creator-agent/internal/chat"
	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"content-creator-agent/internal/storage"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

type processCleanupStore struct {
	fileArtifactStore
	fail bool
}

func (s processCleanupStore) DeleteMany(ctx context.Context, keys []string) error {
	if s.fail {
		return errors.New("simulated storage failure")
	}
	return s.fileArtifactStore.DeleteMany(ctx, keys)
}
func (s processCleanupStore) WalkObjectPages(_ context.Context, prefix string, visit func([]storage.ObjectInfo) error) error {
	var page []storage.ObjectInfo
	err := filepath.WalkDir(s.file(prefix), func(path string, entry fs.DirEntry, err error) error {
		if os.IsNotExist(err) {
			return nil
		}
		if err != nil {
			return err
		}
		if entry.IsDir() || strings.HasSuffix(path, ".type") {
			return nil
		}
		info, err := entry.Info()
		if err != nil {
			return err
		}
		relative, err := filepath.Rel(s.root, path)
		if err != nil {
			return err
		}
		modified := info.ModTime()
		page = append(page, storage.ObjectInfo{Key: filepath.ToSlash(relative), LastModified: &modified})
		return nil
	})
	if err != nil {
		return err
	}
	return visit(page)
}

func TestReconcileProcessHelper(t *testing.T) {
	if os.Getenv("RECONCILE_TEST_CHILD") != "1" {
		t.Skip("subprocess helper")
	}
	gdb, err := db.ConnectWithURL(os.Getenv("INTEGRATION_DATABASE_URL"))
	require.NoError(t, err)
	defer func() {
		sqlDB, e := gdb.DB()
		if e == nil {
			_ = sqlDB.Close()
		}
	}()
	store := processCleanupStore{fileArtifactStore: fileArtifactStore{root: os.Getenv("RECONCILE_TEST_STORE")}, fail: os.Getenv("RECONCILE_TEST_FAIL") == "1"}
	err = jobs.ReconcileArtifacts(context.Background(), gdb, store, time.Now().UTC().Add(-24*time.Hour))
	if store.fail {
		require.Error(t, err)
	} else {
		require.NoError(t, err)
	}
}

func TestReconcileRecoversAfterProcessRestart(t *testing.T) {
	env := newTestEnv(t, nil)
	ctx := context.Background()
	uid, chatID, jobID, contentID := uuid.New(), uuid.New(), uuid.New(), uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: uid, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() {
		env.DB.Delete(&db.User{}, "id = ?", uid)
		env.DB.Exec("DELETE FROM chat_cleanup_tasks WHERE chat_id = ?", chatID)
	})
	require.NoError(t, env.DB.Create(&db.Chat{ID: chatID, UserID: uid, PostType: db.PostTypeSingle}).Error)
	require.NoError(t, env.DB.Create(&db.Job{ID: jobID, ChatID: chatID, UserID: uid, Status: db.JobStatusFailed}).Error)
	require.NoError(t, env.DB.Create(&db.ChatContent{ID: contentID, ChatID: chatID, Role: db.ChatContentRoleAssistant, Content: "ok"}).Error)
	prefix := "slides/" + jobID.String() + "/"
	known := prefix + "slide_01.jpeg"
	late := prefix + "assets/late.png"
	require.NoError(t, env.DB.Create(&db.ChatContentImage{ID: uuid.New(), ChatContentID: contentID, S3Key: known, URL: "url", SlideNumber: 1}).Error)
	root := t.TempDir()
	files := fileArtifactStore{root: root}
	for _, key := range []string{known, late} {
		require.NoError(t, files.Upload(ctx, key, []byte("test")))
		old := time.Now().UTC().Add(-48 * time.Hour)
		require.NoError(t, os.Chtimes(files.file(key), old, old))
	}
	service := chat.NewService(chat.NewRepository(env.DB), jobs.NewRepository(env.DB), failingCleanupStore{}, nil, nil, nil)
	require.NoError(t, service.DeleteChat(ctx, uid, chatID))
	require.NoError(t, env.DB.Table("chat_cleanup_tasks").Where("chat_id = ?", chatID).Update("created_at", time.Now().UTC().Add(-48*time.Hour)).Error)
	executable, err := os.Executable()
	require.NoError(t, err)
	run := func(fail string) {
		t.Helper()
		cmd := exec.Command(executable, "-test.run=^TestReconcileProcessHelper$")
		cmd.Env = append(os.Environ(), "RECONCILE_TEST_CHILD=1", "RECONCILE_TEST_STORE="+root, "RECONCILE_TEST_FAIL="+fail)
		output, err := cmd.CombinedOutput()
		require.NoError(t, err, string(output))
	}
	run("1")
	require.NoError(t, files.HeadObject(ctx, known))
	require.NoError(t, files.HeadObject(ctx, late))
	run("0")
	require.ErrorIs(t, files.HeadObject(ctx, known), storage.ErrObjectNotFound)
	require.ErrorIs(t, files.HeadObject(ctx, late), storage.ErrObjectNotFound)
	var count int64
	require.NoError(t, env.DB.Table("chat_cleanup_tasks").Where("chat_id = ?", chatID).Count(&count).Error)
	require.EqualValues(t, 1, count)
}
