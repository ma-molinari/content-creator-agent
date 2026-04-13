package chat

import (
	"context"
	"os"
	"path/filepath"
	"strings"

	"github.com/google/uuid"
)

const auditFileName = "AUDIT.md"
const brandFileName = "BRAND.md"

func userProfileDir(root string, userID uuid.UUID) string {
	return filepath.Join(root, "instagram-audits", userID.String())
}

func fileReadable(path string) bool {
	st, err := os.Stat(path)
	if err != nil {
		return false
	}
	return !st.IsDir() && st.Mode().IsRegular()
}

func (s *Service) profileDir(userID uuid.UUID) string {
	return userProfileDir(strings.TrimSpace(s.profileDataRoot), userID)
}

// IsProfileConfigured reports whether AUDIT.md and BRAND.md exist under PROFILE_DATA_ROOT.
func (s *Service) IsProfileConfigured(ctx context.Context, userID uuid.UUID) (bool, error) {
	_ = ctx
	if strings.TrimSpace(s.profileDataRoot) == "" {
		return false, nil
	}
	dir := s.profileDir(userID)
	audit := filepath.Join(dir, auditFileName)
	brand := filepath.Join(dir, brandFileName)
	return fileReadable(audit) && fileReadable(brand), nil
}

func (s *Service) loadAuditBrandTexts(ctx context.Context, userID uuid.UUID) (audit, brand string, err error) {
	_ = ctx
	if strings.TrimSpace(s.profileDataRoot) == "" {
		return "", "", ErrSetupRequired
	}
	dir := s.profileDir(userID)
	auditPath := filepath.Join(dir, auditFileName)
	brandPath := filepath.Join(dir, brandFileName)
	if !fileReadable(auditPath) || !fileReadable(brandPath) {
		return "", "", ErrSetupRequired
	}
	ab, err := os.ReadFile(auditPath)
	if err != nil {
		return "", "", ErrSetupRequired
	}
	bb, err := os.ReadFile(brandPath)
	if err != nil {
		return "", "", ErrSetupRequired
	}
	return string(ab), string(bb), nil
}
