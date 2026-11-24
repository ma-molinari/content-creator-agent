package profile

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

type retirementStore struct {
	deleted []string
	err     error
}

func (*retirementStore) Upload(context.Context, string, []byte) error { return nil }
func (*retirementStore) GetSignedURL(context.Context, string, time.Duration) (string, error) {
	return "", nil
}
func (*retirementStore) HeadObject(context.Context, string) error          { return nil }
func (*retirementStore) GetObject(context.Context, string) ([]byte, error) { return nil, nil }
func (s *retirementStore) Delete(_ context.Context, key string) error {
	s.deleted = append(s.deleted, key)
	return s.err
}
func (*retirementStore) DeleteMany(context.Context, []string) error { return nil }

func retirementDB(t *testing.T) *gorm.DB {
	t.Helper()
	gdb, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	require.NoError(t, err)
	require.NoError(t, gdb.Exec(`CREATE TABLE jobs (id TEXT PRIMARY KEY, status TEXT)`).Error)
	require.NoError(t, gdb.Exec(`CREATE TABLE user_profile_references (id TEXT PRIMARY KEY, user_id TEXT, s3_key TEXT, sort_order INTEGER, created_at DATETIME)`).Error)
	return gdb
}

func TestRetireReferencesPreservesOtherAssetsAndRetries(t *testing.T) {
	gdb := retirementDB(t)
	userID, id := uuid.New(), uuid.New()
	key := "users/" + userID.String() + "/design-refs/" + uuid.NewString() + ".png"
	require.NoError(t, gdb.Exec(`INSERT INTO user_profile_references (id,user_id,s3_key,sort_order,created_at) VALUES (?,?,?,0,?)`, id, userID, key, time.Now()).Error)
	store := &retirementStore{err: errors.New("storage unavailable")}
	count, err := RetireReferences(context.Background(), gdb, store)
	require.Error(t, err)
	require.Zero(t, count)
	store.err = nil
	count, err = RetireReferences(context.Background(), gdb, store)
	require.NoError(t, err)
	require.Equal(t, 1, count)
	require.Equal(t, []string{key, key}, store.deleted)
	count, err = RetireReferences(context.Background(), gdb, store)
	require.NoError(t, err)
	require.Zero(t, count)
}

func TestRetireReferencesRejectsActiveJobsAndUnexpectedKeys(t *testing.T) {
	gdb := retirementDB(t)
	store := &retirementStore{}
	require.NoError(t, gdb.Exec(`INSERT INTO jobs (id,status) VALUES (?,?)`, uuid.New(), "processing").Error)
	_, err := RetireReferences(context.Background(), gdb, store)
	require.Error(t, err)
	require.Empty(t, store.deleted)
	require.NoError(t, gdb.Exec(`DELETE FROM jobs`).Error)
	require.NoError(t, gdb.Exec(`INSERT INTO user_profile_references (id,user_id,s3_key,sort_order,created_at) VALUES (?,?,?,0,?)`, uuid.New(), uuid.New(), "slides/existing/assets/image.png", time.Now()).Error)
	_, err = RetireReferences(context.Background(), gdb, store)
	require.Error(t, err)
	require.Empty(t, store.deleted)
}
