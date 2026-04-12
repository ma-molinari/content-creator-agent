package export

import (
	"context"
	"path/filepath"
	"testing"
	"time"
)

func TestPlaywrightRunner_MissingScript(t *testing.T) {
	t.Parallel()
	r := NewPlaywrightRunner(t.TempDir(), time.Second)
	err := r.ExportJPEGs(context.Background(), t.TempDir())
	if err == nil {
		t.Fatal("expected error when scripts/export-slides.js is missing")
	}
}

func TestPlaywrightRunner_ResolvePath(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	_ = filepath.Join(root, "scripts") // not creating export-slides.js on purpose
	r := NewPlaywrightRunner(root, 0)
	if r.timeout != 120*time.Second {
		t.Fatalf("default timeout: %v", r.timeout)
	}
}
