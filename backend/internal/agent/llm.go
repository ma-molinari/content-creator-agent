package agent

import (
	"context"
	"errors"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/tmc/langchaingo/llms"
	"github.com/tmc/langchaingo/llms/openai"
	"github.com/tmc/langchaingo/prompts"
)

const (
	llmRequestTimeout = 60 * time.Second
	llmMaxOutTokens   = 4000
	llmMaxAttempts    = 3
)

// LLMClient wraps the Langchain OpenAI model with retries and timeouts.
type LLMClient struct {
	model llms.Model
}

// Model exposes the underlying langchaingo model for advanced chains (e.g. chains.LLMChain).
func (c *LLMClient) Model() llms.Model {
	if c == nil {
		return nil
	}
	return c.model
}

// NewLLMClient builds an OpenAI-backed client. apiKey must be non-empty for live calls.
func NewLLMClient(apiKey, model string, baseURL string, httpClient *http.Client) (*LLMClient, error) {
	if apiKey == "" {
		return nil, errors.New("agent: OPENAI_API_KEY is required")
	}
	opts := []openai.Option{
		openai.WithToken(apiKey),
		openai.WithModel(model),
	}
	if baseURL != "" {
		opts = append(opts, openai.WithBaseURL(baseURL))
	}
	if httpClient != nil {
		opts = append(opts, openai.WithHTTPClient(httpClient))
	}
	llm, err := openai.New(opts...)
	if err != nil {
		return nil, fmt.Errorf("agent: openai client: %w", err)
	}
	return &LLMClient{model: llm}, nil
}

func isRetryableLLMError(err error) bool {
	if err == nil {
		return false
	}
	if errors.Is(err, context.DeadlineExceeded) || errors.Is(err, context.Canceled) {
		return false
	}
	if llms.IsAuthenticationError(err) || llms.IsInvalidRequestError(err) ||
		llms.IsTokenLimitError(err) || llms.IsContentFilterError(err) {
		return false
	}
	return llms.IsProviderUnavailableError(err) || llms.IsRateLimitError(err) ||
		llms.IsTimeoutError(err) || llms.IsQuotaExceededError(err)
}

// Generate runs a chat completion with system + user messages, bounded output tokens.
func (c *LLMClient) Generate(ctx context.Context, systemPrompt, userPrompt string) (string, error) {
	msgs := []llms.MessageContent{
		llms.TextParts(llms.ChatMessageTypeSystem, systemPrompt),
		llms.TextParts(llms.ChatMessageTypeHuman, userPrompt),
	}
	return c.GenerateChat(ctx, msgs)
}

// GenerateFromChatPrompt renders a langchaingo ChatPromptTemplate (rules + variables) and calls GenerateChat.
// Use this to mirror Cursor-style @ rules: compose system/human via templates instead of raw string concat.
func (c *LLMClient) GenerateFromChatPrompt(ctx context.Context, tmpl prompts.ChatPromptTemplate, values map[string]any) (string, error) {
	pv, err := tmpl.FormatPrompt(values)
	if err != nil {
		return "", fmt.Errorf("agent: format chat prompt: %w", err)
	}
	msgs, err := chatMessagesToMessageContents(pv.Messages())
	if err != nil {
		return "", err
	}
	return c.GenerateChat(ctx, msgs)
}

// GenerateChat sends a message list to the model (system / human / tool roles preserved).
func (c *LLMClient) GenerateChat(ctx context.Context, messages []llms.MessageContent) (string, error) {
	if c == nil || c.model == nil {
		return "", errors.New("agent: llm not configured")
	}
	if len(messages) == 0 {
		return "", errors.New("agent: no messages")
	}

	var lastErr error
	for attempt := 0; attempt < llmMaxAttempts; attempt++ {
		reqCtx, cancel := context.WithTimeout(ctx, llmRequestTimeout)
		resp, err := c.model.GenerateContent(reqCtx, messages,
			llms.WithMaxTokens(llmMaxOutTokens),
		)
		cancel()
		if err == nil && resp != nil && len(resp.Choices) > 0 {
			out := strings.TrimSpace(resp.Choices[0].Content)
			if out != "" {
				return out, nil
			}
			lastErr = errors.New("agent: empty model response")
			log.Printf("agent: llm attempt %d empty content", attempt+1)
		} else if err != nil {
			lastErr = err
			log.Printf("agent: llm attempt %d failed: %v", attempt+1, err)
			if !isRetryableLLMError(err) {
				return "", fmt.Errorf("agent: language model request failed: %w", err)
			}
			if attempt == llmMaxAttempts-1 {
				return "", fmt.Errorf("agent: language model request failed: %w", err)
			}
		} else {
			lastErr = errors.New("agent: empty model response")
		}
		if attempt < llmMaxAttempts-1 {
			d := time.Duration(1<<attempt) * 200 * time.Millisecond
			select {
			case <-ctx.Done():
				return "", ctx.Err()
			case <-time.After(d):
			}
		}
	}
	if lastErr == nil {
		lastErr = errors.New("agent: unknown llm failure")
	}
	return "", lastErr
}

func chatMessagesToMessageContents(chat []llms.ChatMessage) ([]llms.MessageContent, error) {
	out := make([]llms.MessageContent, 0, len(chat))
	for _, m := range chat {
		mc, err := chatMessageToMessageContent(m)
		if err != nil {
			return nil, err
		}
		out = append(out, mc)
	}
	return out, nil
}

func chatMessageToMessageContent(m llms.ChatMessage) (llms.MessageContent, error) {
	switch msg := m.(type) {
	case llms.SystemChatMessage:
		return llms.TextParts(llms.ChatMessageTypeSystem, msg.Content), nil
	case llms.HumanChatMessage:
		return llms.TextParts(llms.ChatMessageTypeHuman, msg.Content), nil
	case llms.AIChatMessage:
		return llms.TextParts(llms.ChatMessageTypeAI, msg.Content), nil
	case llms.GenericChatMessage:
		return llms.TextParts(llms.ChatMessageTypeGeneric, msg.Content), nil
	case llms.ToolChatMessage:
		return llms.MessageContent{
			Role:  llms.ChatMessageTypeTool,
			Parts: []llms.ContentPart{llms.TextPart(msg.Content)},
		}, nil
	case llms.FunctionChatMessage:
		return llms.MessageContent{
			Role:  llms.ChatMessageTypeFunction,
			Parts: []llms.ContentPart{llms.TextPart(msg.Content)},
		}, nil
	default:
		return llms.MessageContent{}, fmt.Errorf("agent: unsupported chat message type %T", m)
	}
}
