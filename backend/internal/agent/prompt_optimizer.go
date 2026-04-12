package agent

import (
	"context"
	"regexp"
	"strings"
	"unicode"
)

var htmlTagPattern = regexp.MustCompile(`<[^>]+>`)

// stripHTML removes simple HTML tags.
func stripHTML(s string) string {
	return htmlTagPattern.ReplaceAllString(s, "")
}

func stripControlChars(s string) string {
	return strings.Map(func(r rune) rune {
		if unicode.IsControl(r) && r != '\n' && r != '\t' {
			return -1
		}
		return r
	}, s)
}

// SanitizeUserInput removes HTML and control characters for safe concatenation.
func SanitizeUserInput(s string) string {
	s = stripHTML(s)
	s = stripControlChars(s)
	return strings.TrimSpace(s)
}

// PromptOptimizer rewrites user prompts using the meta-prompting rules.
type PromptOptimizer struct {
	llm *LLMClient
}

// NewPromptOptimizer constructs an optimizer.
func NewPromptOptimizer(llm *LLMClient) *PromptOptimizer {
	return &PromptOptimizer{llm: llm}
}

// OptimizePrompt returns a structured brief; userProfile may contain AUDIT/BRAND excerpts.
func (p *PromptOptimizer) OptimizePrompt(ctx context.Context, userPrompt, userProfile string) (string, error) {
	if p == nil || p.llm == nil {
		return "", ErrLLMNotConfigured
	}
	user := SanitizeUserInput(userPrompt)
	if user == "" {
		return "", ErrEmptyPrompt
	}
	profile := SanitizeUserInput(userProfile)
	if profile != "" {
		user = "Perfil do usuário (referência):\n" + profile + "\n\nPedido do usuário:\n" + user
	}
	return p.llm.GenerateFromChatPrompt(ctx, CreateSocialPostsOptimizerChatPrompt(), map[string]any{"user": user})
}
