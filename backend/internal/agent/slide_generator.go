package agent

import (
	"context"
	"fmt"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/google/uuid"
)

// SlideHTML is one generated carousel slide file.
type SlideHTML struct {
	Name string
	HTML string
}

var slideDelimiter = regexp.MustCompile(`(?m)^###SLIDE_FILE:([^\s#]+\.html)###\s*`)

const slideGenSystemPrefix = `You are an expert Instagram carousel designer. Output self-contained HTML slides for a fixed canvas 768×1376px (9:16), with embedded CSS in each file or a shared style block. Follow image-designer rules: minimum type sizes (hero ~58px, heading ~43px, body ~34px, caption ~24px), font-weight ≥500 for body, strong contrast, no slide counter on the image.

Use the brand and audit context provided in the user message to stay aligned with palette, tone, and feed evidence.

Output format (strict):
- Emit one block per slide.
- Each block MUST start with a line exactly: ###SLIDE_FILE:slide-NN.html### where NN is zero-padded two digits (slide-01.html, slide-02.html, ...).
- After that line, output the full HTML document for that slide until the next ###SLIDE_FILE: line or end of output.
- Do not wrap the HTML in markdown code fences.
`

// SlideGenerator produces slide HTML from an optimized prompt and profile files.
type SlideGenerator struct {
	llm     *LLMClient
	profile *ProfileChecker
}

// NewSlideGenerator constructs a generator.
func NewSlideGenerator(llm *LLMClient, profile *ProfileChecker) *SlideGenerator {
	return &SlideGenerator{llm: llm, profile: profile}
}

// GenerateSlides loads AUDIT/BRAND, then asks the model for slide HTML.
func (g *SlideGenerator) GenerateSlides(ctx context.Context, userID uuid.UUID, optimizedPrompt string) ([]SlideHTML, error) {
	if g == nil || g.llm == nil {
		return nil, ErrLLMNotConfigured
	}
	if g.profile == nil {
		return nil, ErrSetupRequired
	}
	profileText, err := g.profile.LoadProfileText(ctx, userID)
	if err != nil {
		return nil, err
	}
	user := "--- Contexto de perfil ---\n" + profileText +
		"\n\n--- Brief otimizado ---\n" + strings.TrimSpace(optimizedPrompt)

	raw, err := g.llm.Generate(ctx, slideGenSystemPrefix, user)
	if err != nil {
		return nil, err
	}
	slides, err := parseSlides(raw)
	if err != nil {
		return nil, fmt.Errorf("agent: parse slides: %w", err)
	}
	if len(slides) == 0 {
		return nil, fmt.Errorf("agent: model returned no slides")
	}
	for i := range slides {
		slides[i].Name = filepath.Base(strings.TrimSpace(slides[i].Name))
	}
	return slides, nil
}

func parseSlides(raw string) ([]SlideHTML, error) {
	raw = strings.TrimSpace(raw)
	idx := slideDelimiter.FindAllStringSubmatchIndex(raw, -1)
	if len(idx) == 0 {
		return nil, fmt.Errorf("no SLIDE_FILE markers found")
	}
	var out []SlideHTML
	for i, loc := range idx {
		name := raw[loc[2]:loc[3]]
		contentStart := loc[1]
		var contentEnd int
		if i+1 < len(idx) {
			contentEnd = idx[i+1][0]
		} else {
			contentEnd = len(raw)
		}
		html := strings.TrimSpace(raw[contentStart:contentEnd])
		html = strings.TrimSpace(html)
		if html == "" {
			continue
		}
		out = append(out, SlideHTML{Name: name, HTML: html})
	}
	return out, nil
}
