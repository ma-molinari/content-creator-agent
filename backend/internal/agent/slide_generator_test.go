package agent

import (
	"strings"
	"testing"

	"github.com/google/uuid"
)

func TestParseSlides(t *testing.T) {
	t.Parallel()
	raw := `
###SLIDE_FILE:slide-01.html###
<!DOCTYPE html><html><body>one</body></html>
###SLIDE_FILE:slide-02.html###
<!DOCTYPE html><html><body>two</body></html>
`
	slides, err := parseSlides(raw)
	if err != nil {
		t.Fatal(err)
	}
	if len(slides) != 2 {
		t.Fatalf("want 2 slides, got %d", len(slides))
	}
	if slides[0].Name != "slide-01.html" || !strings.Contains(slides[0].HTML, "one") {
		t.Fatalf("slide 0: %+v", slides[0])
	}
}

func TestSlideGenerator_ErrLLMNotConfigured(t *testing.T) {
	t.Parallel()
	g := NewSlideGenerator(nil, NewProfileChecker(""))
	_, err := g.GenerateSlides(t.Context(), uuid.New(), "brief")
	if err != ErrLLMNotConfigured {
		t.Fatalf("want ErrLLMNotConfigured, got %v", err)
	}
}
