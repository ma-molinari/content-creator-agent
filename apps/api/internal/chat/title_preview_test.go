package chat

import (
	"strings"
	"testing"

	"content-creator-agent/internal/db"

	"github.com/google/uuid"
)

func TestTitlePreviewFromBody_empty(t *testing.T) {
	if g := titlePreviewFromBody(""); g != "" {
		t.Fatalf("got %q", g)
	}
	if g := titlePreviewFromBody("   \n\t  "); g != "" {
		t.Fatalf("got %q", g)
	}
}

func TestTitlePreviewFromBody_shortUnchanged(t *testing.T) {
	s := "Hello, first prompt"
	if g := titlePreviewFromBody(s); g != s {
		t.Fatalf("got %q want %q", g, s)
	}
}

func TestTitlePreviewFromBody_truncatesRunesNotBytes(t *testing.T) {
	// 81× 'é' = 162 UTF-8 bytes, 81 runes — should truncate to 80 runes
	body := strings.Repeat("é", 81)
	got := titlePreviewFromBody(body)
	runes := []rune(got)
	if len(runes) != titlePreviewMaxRunes {
		t.Fatalf("want %d runes, got %d", titlePreviewMaxRunes, len(runes))
	}
	if got != strings.Repeat("é", titlePreviewMaxRunes) {
		t.Fatalf("unexpected truncation content")
	}
}

func TestTitlePreviewFromBody_exactly80Runes(t *testing.T) {
	body := strings.Repeat("a", titlePreviewMaxRunes)
	if g := titlePreviewFromBody(body); g != body {
		t.Fatalf("got %q", g)
	}
}

func TestChatNeedsTitle(t *testing.T) {
	if !chatNeedsTitle(&db.Chat{ID: uuid.New()}) {
		t.Fatal("nil title should need title")
	}
	empty := ""
	if !chatNeedsTitle(&db.Chat{Title: &empty}) {
		t.Fatal("empty title should need title")
	}
	ws := "  "
	if !chatNeedsTitle(&db.Chat{Title: &ws}) {
		t.Fatal("whitespace-only title should need title")
	}
	set := "Already set"
	if chatNeedsTitle(&db.Chat{Title: &set}) {
		t.Fatal("non-empty title should not need title")
	}
}
