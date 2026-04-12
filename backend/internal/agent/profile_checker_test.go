package agent

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/google/uuid"
)

func TestProfileChecker_CheckProfileSetup(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	uid := uuid.New()
	dir := filepath.Join(root, "instagram-audits", uid.String())
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "AUDIT.md"), []byte("a"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "BRAND.md"), []byte("b"), 0o600); err != nil {
		t.Fatal(err)
	}
	pc := NewProfileChecker(root)
	ok, err := pc.CheckProfileSetup(t.Context(), uid)
	if err != nil {
		t.Fatal(err)
	}
	if !ok {
		t.Fatal("expected configured")
	}
	text, err := pc.LoadProfileText(t.Context(), uid)
	if err != nil || !strings.Contains(text, "AUDIT") || !strings.Contains(text, "BRAND") {
		t.Fatalf("profile text: %v %q", err, text)
	}
}
