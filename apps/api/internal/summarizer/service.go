package summarizer

import (
	"context"
	"errors"
	"log"
	"strings"
	"time"

	"content-creator-agent/internal/db"

	"github.com/google/uuid"
)

const runTimeout = 5 * time.Minute

// SummarizerRepository lists DB operations used by the summarizer (implemented by *Repository).
type SummarizerRepository interface {
	ListEligibleChatIDs(ctx context.Context) ([]uuid.UUID, error)
	ListContentsOrdered(ctx context.Context, chatID uuid.UUID) ([]db.ChatContent, error)
	UpsertResume(ctx context.Context, chatID uuid.UUID, summary string, lastContentAt, summarizedAt time.Time) error
}

// SummarizerClient produces summaries from chat text (implemented by *Client).
type SummarizerClient interface {
	Summarize(ctx context.Context, history string) (string, error)
}

// Service orchestrates eligibility, history assembly, OpenAI, and persistence.
type Service struct {
	repo   SummarizerRepository
	openai SummarizerClient
}

// NewService constructs the summarizer service.
func NewService(repo *Repository, oa *Client) *Service {
	return &Service{repo: repo, openai: oa}
}

// Run processes all eligible chats. Errors on individual chats are logged; the batch continues.
func (s *Service) Run(parent context.Context) {
	start := time.Now()
	ctx, cancel := context.WithTimeout(parent, runTimeout)
	defer cancel()

	log.Printf("[summarizer] run started")
	eligible, err := s.repo.ListEligibleChatIDs(ctx)
	if err != nil {
		log.Printf("[summarizer] list eligible chats: %v", err)
		return
	}

	var ok, fail int
	for _, chatID := range eligible {
		if err := ctx.Err(); err != nil {
			if errors.Is(err, context.DeadlineExceeded) {
				log.Printf("[WARN] summarizer: run exceeded 5-minute budget")
			}
			break
		}
		if err := s.summarizeChat(ctx, chatID); err != nil {
			log.Printf("[ERROR] summarizer: chat %s: %v", chatID, err)
			fail++
			continue
		}
		ok++
	}

	dur := time.Since(start)
	if ctx.Err() == nil {
		log.Printf("[summarizer] run finished duration=%s processed=%d errors=%d", dur, ok, fail)
	} else if errors.Is(ctx.Err(), context.DeadlineExceeded) {
		log.Printf("[summarizer] run stopped (timeout) duration=%s processed=%d errors=%d", dur, ok, fail)
	}
}

func (s *Service) summarizeChat(ctx context.Context, chatID uuid.UUID) error {
	contents, err := s.repo.ListContentsOrdered(ctx, chatID)
	if err != nil {
		return err
	}
	if len(contents) == 0 {
		return nil
	}

	var b strings.Builder
	var lastAt time.Time
	for _, m := range contents {
		if m.CreatedAt.After(lastAt) {
			lastAt = m.CreatedAt
		}
		line := string(m.Role) + ": " + strings.TrimSpace(m.Content) + "\n"
		b.WriteString(line)
	}

	summary, err := s.openai.Summarize(ctx, b.String())
	if err != nil {
		return err
	}
	if summary == "" {
		return errors.New("empty summary from model")
	}

	now := time.Now().UTC()
	if err := s.repo.UpsertResume(ctx, chatID, summary, lastAt, now); err != nil {
		return err
	}

	log.Printf("[summarizer] chat %s summarized last_content_at=%s", chatID, lastAt.UTC().Format(time.RFC3339))
	return nil
}
