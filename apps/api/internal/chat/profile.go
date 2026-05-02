package chat

import (
	"context"

	"content-creator-agent/internal/profile"

	"github.com/google/uuid"
)

// IsProfileConfigured reports whether profile text exists in the database (both non-empty after TrimSpace).
// When profileRepo is nil, the profile is never considered configured.
func (s *Service) IsProfileConfigured(ctx context.Context, userID uuid.UUID) (bool, error) {
	if s.profileRepo == nil {
		return false, nil
	}
	p, err := s.profileRepo.GetByUserID(ctx, userID)
	if err != nil {
		return false, err
	}
	if p == nil || !profile.TextsConfigured(p.AuditText, p.BrandText) {
		return false, nil
	}
	return true, nil
}

func (s *Service) loadAuditBrandTexts(ctx context.Context, userID uuid.UUID) (audit, brand string, err error) {
	if s.profileRepo == nil {
		return "", "", ErrSetupRequired
	}
	p, err := s.profileRepo.GetByUserID(ctx, userID)
	if err != nil {
		return "", "", err
	}
	if p == nil || !profile.TextsConfigured(p.AuditText, p.BrandText) {
		return "", "", ErrSetupRequired
	}
	return p.AuditText, p.BrandText, nil
}
