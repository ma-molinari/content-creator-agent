package summarizer

import (
	"context"
	"errors"
	"strings"

	"github.com/sashabaranov/go-openai"
)

const summarizeSystemPrompt = `You summarize chat histories for a creative content assistant. Produce a compact summary in the same language as the messages when possible.
Preserve: user goals, creative briefs, brand/voice constraints, explicit requests for changes, and important decisions.
De-emphasize or omit: boilerplate, raw slide HTML/markup, and long assistant outputs that duplicate what slides already show.
Reply with plain text only, no markdown headings unless the user used them.`

// Client wraps OpenAI chat completions for summarization.
type Client struct {
	inner *openai.Client
}

// NewClient builds a summarizer client from an API key.
func NewClient(apiKey string) *Client {
	return &Client{inner: openai.NewClient(apiKey)}
}

// Summarize turns ordered chat text into a short summary.
func (c *Client) Summarize(ctx context.Context, history string) (string, error) {
	history = strings.TrimSpace(history)
	if history == "" {
		return "", errors.New("empty history")
	}
	resp, err := c.inner.CreateChatCompletion(ctx, openai.ChatCompletionRequest{
		Model: "gpt-5.4-mini",
		Messages: []openai.ChatCompletionMessage{
			{Role: openai.ChatMessageRoleSystem, Content: summarizeSystemPrompt},
			{Role: openai.ChatMessageRoleUser, Content: history},
		},
		MaxCompletionTokens: 512,
	})
	if err != nil {
		return "", err
	}
	if len(resp.Choices) == 0 {
		return "", errors.New("no completion choices")
	}
	return strings.TrimSpace(resp.Choices[0].Message.Content), nil
}
