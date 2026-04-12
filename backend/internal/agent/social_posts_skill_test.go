package agent

import (
	"strings"
	"testing"
)

func TestCreateSocialPostsOptimizerChatPrompt_renders(t *testing.T) {
	t.Parallel()
	tmpl := CreateSocialPostsOptimizerChatPrompt()
	pv, err := tmpl.FormatPrompt(map[string]any{"user": "brief request"})
	if err != nil {
		t.Fatal(err)
	}
	msgs := pv.Messages()
	if len(msgs) < 2 {
		t.Fatalf("expected at least 2 chat messages, got %d", len(msgs))
	}
	combined := msgs[0].GetContent() + msgs[1].GetContent()
	if !strings.Contains(combined, "Context-gated marketing content") {
		t.Fatal("expected skill body in rendered prompt")
	}
}

func TestCreateSocialPostsSlideChatPrompt_renders(t *testing.T) {
	t.Parallel()
	tmpl := CreateSocialPostsSlideChatPrompt()
	pv, err := tmpl.FormatPrompt(map[string]any{"user": "slide brief"})
	if err != nil {
		t.Fatal(err)
	}
	msgs := pv.Messages()
	if len(msgs) < 2 {
		t.Fatalf("expected at least 2 chat messages, got %d", len(msgs))
	}
	combined := msgs[0].GetContent() + msgs[1].GetContent()
	if !strings.Contains(combined, "Marketing Carousel Growth Engine") {
		t.Fatal("expected carousel rule in rendered prompt")
	}
}
