package export

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

// PlaywrightRunner runs scripts/export-slides.js against a carousel directory.
type PlaywrightRunner struct {
	repoRoot string
	timeout  time.Duration
	nodePath string
}

// NewPlaywrightRunner builds a runner. repoRoot must contain scripts/export-slides.js.
func NewPlaywrightRunner(repoRoot string, timeout time.Duration) *PlaywrightRunner {
	if timeout <= 0 {
		timeout = 120 * time.Second
	}
	node := os.Getenv("NODE_BINARY")
	if node == "" {
		node = "node"
	}
	return &PlaywrightRunner{repoRoot: repoRoot, timeout: timeout, nodePath: node}
}

// ExportJPEGs writes slide-NN.jpg in carouselDir using Playwright (requires node + playwright).
func (r *PlaywrightRunner) ExportJPEGs(ctx context.Context, carouselDir string) error {
	if r == nil {
		return fmt.Errorf("export: runner not configured")
	}
	root := r.repoRoot
	if root == "" {
		return fmt.Errorf("export: REPO_ROOT is not set")
	}
	script := filepath.Join(root, "scripts", "export-slides.js")
	if st, err := os.Stat(script); err != nil || st.IsDir() {
		return fmt.Errorf("export: export script not found at %s", script)
	}
	absDir, err := filepath.Abs(carouselDir)
	if err != nil {
		return fmt.Errorf("export: carousel path: %w", err)
	}
	ctx, cancel := context.WithTimeout(ctx, r.timeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, r.nodePath, script, "--export", "--confirm", absDir)
	var stderr bytes.Buffer
	cmd.Dir = root
	cmd.Stdout = io.Discard
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		log.Printf("export: playwright stderr: %s", stderr.String())
		return fmt.Errorf("export: slide JPEG export failed: %w", err)
	}
	if stderr.Len() > 0 {
		log.Printf("export: playwright stderr: %s", stderr.String())
	}
	return nil
}
