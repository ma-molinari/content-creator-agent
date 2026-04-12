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

	raw, err := g.llm.GenerateFromChatPrompt(ctx, CreateSocialPostsSlideChatPrompt(), map[string]any{"user": user})
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
