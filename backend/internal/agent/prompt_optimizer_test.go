package agent

import (
	"strings"
	"testing"

	"content-creator-agent/internal/agent/promptdata"
)

func TestSanitizeUserInput_HTMLAndControls(t *testing.T) {
	t.Parallel()
	in := "Hello <b>world</b> \x00\x01 text"
	out := SanitizeUserInput(in)
	if strings.Contains(out, "<") || strings.Contains(out, "\x00") {
		t.Fatalf("unexpected: %q", out)
	}
}

func TestPromptOptimizer_structureHint(t *testing.T) {
	t.Parallel()
	s := promptdata.OptimizerSystemPrompt()
	if !strings.Contains(s, "### Persona") {
		t.Fatal("expected persona section in system prompt")
	}
}
