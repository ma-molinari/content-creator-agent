//go:build integration

package integration

import (
	"context"
	"testing"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/profile"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

func TestReferenceSourcesAreUserScoped(t *testing.T) {
	env := newTestEnv(t, nil)
	owner, other := uuid.New(), uuid.New()
	for _, id := range []uuid.UUID{owner, other} {
		require.NoError(t, env.DB.Create(&db.User{ID: id, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
		id := id
		t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", id) })
	}
	repo := profile.NewReferencesRepository(env.DB)
	first, err := repo.Create(context.Background(), owner, "users/owner/ref.jpg")
	require.NoError(t, err)
	_, err = repo.Create(context.Background(), other, "users/other/ref.jpg")
	require.NoError(t, err)
	service := profile.NewService(profile.NewRepository(env.DB), repo, mockStorage{}, 8, 5*1024*1024)
	sources, err := service.ListReferenceSources(context.Background(), owner)
	require.NoError(t, err)
	require.Equal(t, map[string]string{first.ID.String(): "users/owner/ref.jpg"}, sources)
}
