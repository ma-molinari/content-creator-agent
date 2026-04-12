package agent

import (
	"content-creator-agent/internal/agent/promptdata"

	"github.com/tmc/langchaingo/prompts"
)

// SocialPostsSkill mirrors the Cursor skill "create-social-posts": ordered rule bundles
// (promptdata.Rule*) + langchaingo ChatPromptTemplate for system/human composition.
//
// Use CreateSocialPostsOptimizerChatPrompt / CreateSocialPostsSlideChatPrompt with
// LLMClient.GenerateFromChatPrompt to align with LangChain-style prompt objects instead
// of raw string concatenation.
type SocialPostsSkill struct{}

// OptimizerRuleIDs returns the policy document stack for the brief optimizer (observability).
func (SocialPostsSkill) OptimizerRuleIDs() []promptdata.RuleID {
	out := make([]promptdata.RuleID, len(promptdata.OptimizerBundle))
	copy(out, promptdata.OptimizerBundle)
	return out
}

// SlideGeneratorRuleIDs returns the policy document stack for slide HTML generation.
func (SocialPostsSkill) SlideGeneratorRuleIDs() []promptdata.RuleID {
	out := make([]promptdata.RuleID, len(promptdata.SlideGeneratorBundle))
	copy(out, promptdata.SlideGeneratorBundle)
	return out
}

// CreateSocialPostsOptimizerChatPrompt builds a ChatPromptTemplate for the prompt optimizer.
// Partial "system" loads the full Optimizer bundle (API context + skill + checklist + feed + meta).
func CreateSocialPostsOptimizerChatPrompt() prompts.ChatPromptTemplate {
	return prompts.ChatPromptTemplate{
		Messages: []prompts.MessageFormatter{
			prompts.NewSystemMessagePromptTemplate("{{.system}}", []string{"system"}),
			prompts.NewHumanMessagePromptTemplate("{{.user}}", []string{"user"}),
		},
		PartialVariables: map[string]any{
			"system": func() string { return promptdata.OptimizerSystemPrompt() },
		},
	}
}

// CreateSocialPostsSlideChatPrompt builds a ChatPromptTemplate for carousel slide generation.
func CreateSocialPostsSlideChatPrompt() prompts.ChatPromptTemplate {
	return prompts.ChatPromptTemplate{
		Messages: []prompts.MessageFormatter{
			prompts.NewSystemMessagePromptTemplate("{{.system}}", []string{"system"}),
			prompts.NewHumanMessagePromptTemplate("{{.user}}", []string{"user"}),
		},
		PartialVariables: map[string]any{
			"system": func() string { return promptdata.SlideGeneratorSystemPrompt() },
		},
	}
}
