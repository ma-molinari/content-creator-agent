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
	if c == nil || c.model == nil {
		return "", errors.New("agent: llm not configured")
	}
	msgs := []llms.MessageContent{
		{
			Role:  llms.ChatMessageTypeSystem,
			Parts: []llms.ContentPart{llms.TextContent{Text: systemPrompt}},
		},
		{
			Role:  llms.ChatMessageTypeHuman,
			Parts: []llms.ContentPart{llms.TextContent{Text: userPrompt}},
		},
	}

	var lastErr error
	for attempt := 0; attempt < llmMaxAttempts; attempt++ {
		reqCtx, cancel := context.WithTimeout(ctx, llmRequestTimeout)
		resp, err := c.model.GenerateContent(reqCtx, msgs,
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
