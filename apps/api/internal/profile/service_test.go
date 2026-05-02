package profile

import (
	"context"
	"testing"

	"content-creator-agent/internal/db"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

type stubRepo struct {
	p   *db.UserProfile
	err error
}

func (s *stubRepo) GetByUserID(context.Context, uuid.UUID) (*db.UserProfile, error) {
	return s.p, s.err
}

func (s *stubRepo) Upsert(context.Context, uuid.UUID, string, string) error {
	return nil
}

func TestGetProfile_empty(t *testing.T) {
	svc := &Service{repo: &stubRepo{p: nil}}
	v, err := svc.GetProfile(context.Background(), uuid.New())
	require.NoError(t, err)
	require.False(t, v.Configured)
	require.Equal(t, "", v.AuditText)
	require.Equal(t, "", v.BrandText)
}

func TestGetProfile_configured(t *testing.T) {
	uid := uuid.New()
	svc := &Service{repo: &stubRepo{p: &db.UserProfile{
		UserID:    uid,
		AuditText: " audit ",
		BrandText: " brand ",
	}}}
	v, err := svc.GetProfile(context.Background(), uid)
	require.NoError(t, err)
	require.True(t, v.Configured)
	require.Equal(t, " audit ", v.AuditText)
}

func TestGetProfile_notConfiguredIfOneEmpty(t *testing.T) {
	svc := &Service{repo: &stubRepo{p: &db.UserProfile{
		AuditText: "x",
		BrandText: "   ",
	}}}
	v, err := svc.GetProfile(context.Background(), uuid.New())
	require.NoError(t, err)
	require.False(t, v.Configured)
}

func TestTextsConfigured(t *testing.T) {
	require.True(t, TextsConfigured("a", "b"))
	require.False(t, TextsConfigured("", "b"))
	require.False(t, TextsConfigured("a", ""))
	require.False(t, TextsConfigured(" ", "\t"))
}
