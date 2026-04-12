package promptdata

import (
	"fmt"
	"strings"
)

// RuleID identifies an embedded policy document (mirror of .cursor/rules or skill chunks).
// Filenames match go:embed *.md in this package.
type RuleID string

const (
	RuleAPICarouselContext       RuleID = "api_carousel_context.md"
	RuleCreateSocialPostsSkill   RuleID = "create-social-posts_skill.md"
	RuleContextChecklist         RuleID = "context-checklist.md"
	RuleInstagramFeed            RuleID = "instagram-feed.md"
	RuleOptimizerInstructions    RuleID = "optimizer_instructions.md"
	RuleImageDesigner            RuleID = "image-designer.md"
	RuleDesignUIDesigner         RuleID = "design-ui-designer.md"
	RuleMarketingCarouselGrowth  RuleID = "marketing-carousel-growth-engine.md"
	RuleSlideOutputFormat        RuleID = "slide_output_format.md"
)

// OptimizerBundle is the ordered rule stack for PromptOptimizer (create-social-posts brief / API).
var OptimizerBundle = []RuleID{
	RuleAPICarouselContext,
	RuleCreateSocialPostsSkill,
	RuleContextChecklist,
	RuleInstagramFeed,
	RuleOptimizerInstructions,
}

// SlideGeneratorBundle is the ordered rule stack for carousel slide HTML generation.
var SlideGeneratorBundle = []RuleID{
	RuleAPICarouselContext,
	RuleImageDesigner,
	RuleDesignUIDesigner,
	RuleMarketingCarouselGrowth,
	RuleSlideOutputFormat,
}

// Rule returns the markdown body for a single rule.
func Rule(id RuleID) (string, error) {
	b, err := files.ReadFile(string(id))
	if err != nil {
		return "", fmt.Errorf("promptdata: read %q: %w", id, err)
	}
	return string(b), nil
}

// MustRule returns the markdown body or panics (compile-time embed guarantees existence).
func MustRule(id RuleID) string {
	return mustRead(string(id))
}

// JoinRules concatenates rules in order with the same separator as legacy prompts.
func JoinRules(ids []RuleID) (string, error) {
	var parts []string
	for _, id := range ids {
		b, err := Rule(id)
		if err != nil {
			return "", fmt.Errorf("promptdata: rule %q: %w", id, err)
		}
		parts = append(parts, string(b))
	}
	return strings.Join(parts, "\n\n---\n\n"), nil
}

// MustJoinRules is like JoinRules but panics on missing files.
func MustJoinRules(ids []RuleID) string {
	var parts []string
	for _, id := range ids {
		parts = append(parts, MustRule(id))
	}
	return strings.Join(parts, "\n\n---\n\n")
}
