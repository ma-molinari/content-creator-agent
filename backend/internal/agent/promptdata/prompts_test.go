package promptdata

import (
	"strings"
	"testing"
)

func TestOptimizerSystemPrompt_embeddedMarkers(t *testing.T) {
	t.Parallel()
	s := OptimizerSystemPrompt()
	if !strings.Contains(s, "API carousel context") {
		t.Fatal("expected api_carousel_context marker")
	}
	if !strings.Contains(s, "### Persona") {
		t.Fatal("expected optimizer_instructions persona heading")
	}
	if !strings.Contains(s, "Context-gated marketing content") {
		t.Fatal("expected synced SKILL body (create-social-posts)")
	}
	if !strings.Contains(s, "Platform Rules") {
		t.Fatal("expected synced instagram-feed body")
	}
}

func TestSlideGeneratorSystemPrompt_embeddedMarkers(t *testing.T) {
	t.Parallel()
	s := SlideGeneratorSystemPrompt()
	if !strings.Contains(s, "API carousel context") {
		t.Fatal("expected api_carousel_context marker")
	}
	if !strings.Contains(s, "###SLIDE_FILE:slide-NN.html###") {
		t.Fatal("expected slide output format delimiters")
	}
	if !strings.Contains(s, "Visual Design & Image Creation") {
		t.Fatal("expected synced image-designer body")
	}
	if !strings.Contains(s, "Marketing Carousel Growth Engine") {
		t.Fatal("expected synced marketing-carousel-growth-engine body")
	}
}
