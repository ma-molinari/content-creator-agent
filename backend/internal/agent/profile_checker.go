package agent

import (
	"context"
	"os"
	"path/filepath"
	"strings"

	"github.com/google/uuid"
)

const (
	auditFileName = "AUDIT.md"
	brandFileName = "BRAND.md"
)

// ProfileChecker resolves profile paths under PROFILE_DATA_ROOT.
type ProfileChecker struct {
	root string
}

// NewProfileChecker builds a checker. root is PROFILE_DATA_ROOT (may be empty for tests with overrides).
func NewProfileChecker(root string) *ProfileChecker {
	return &ProfileChecker{root: root}
}

// UserProfileDir returns instagram-audits/<user_id>/ under the data root.
func (p *ProfileChecker) UserProfileDir(userID uuid.UUID) string {
	if p == nil {
		return ""
	}
	return filepath.Join(p.root, "instagram-audits", userID.String())
}

// CheckProfileSetup reports whether both AUDIT.md and BRAND.md exist and are readable regular files.
func (p *ProfileChecker) CheckProfileSetup(ctx context.Context, userID uuid.UUID) (bool, error) {
	_ = ctx
	if p == nil || strings.TrimSpace(p.root) == "" {
		return false, nil
	}
	dir := p.UserProfileDir(userID)
	audit := filepath.Join(dir, auditFileName)
	brand := filepath.Join(dir, brandFileName)
	if !fileReadable(audit) || !fileReadable(brand) {
		return false, nil
	}
	return true, nil
}

func fileReadable(path string) bool {
	st, err := os.Stat(path)
	if err != nil {
		return false
	}
	return !st.IsDir() && st.Mode().IsRegular()
}

// LoadProfileText returns concatenated AUDIT and BRAND contents for prompt context.
func (p *ProfileChecker) LoadProfileText(ctx context.Context, userID uuid.UUID) (string, error) {
	_ = ctx
	if p == nil || strings.TrimSpace(p.root) == "" {
		return "", ErrSetupRequired
	}
	dir := p.UserProfileDir(userID)
	auditPath := filepath.Join(dir, auditFileName)
	brandPath := filepath.Join(dir, brandFileName)
	if !fileReadable(auditPath) || !fileReadable(brandPath) {
		return "", ErrSetupRequired
	}
	auditBytes, err := os.ReadFile(auditPath)
	if err != nil {
		return "", ErrSetupRequired
	}
	brandBytes, err := os.ReadFile(brandPath)
	if err != nil {
		return "", ErrSetupRequired
	}
	var b strings.Builder
	b.WriteString("## AUDIT.md\n")
	b.Write(auditBytes)
	b.WriteString("\n\n## BRAND.md\n")
	b.Write(brandBytes)
	return b.String(), nil
}
