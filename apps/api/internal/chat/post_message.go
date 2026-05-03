package chat

import (
	"context"
	"log"
	"regexp"
	"strings"
	"unicode"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"

	"github.com/google/uuid"
)

var (
	htmlTagPattern         = regexp.MustCompile(`<[^>]+>`)
	chatSlideMarkerPattern = regexp.MustCompile(`(?i)###SLIDE_FILE:[^\n]*`)
	chatEndSlidePattern    = regexp.MustCompile(`(?i)###END_SLIDE###`)
)

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

// neutralizePipelineDelimiters prefixes horizontal rules and removes slide
// markers so a crafted message cannot hijack the worker pipeline separators.
func neutralizePipelineDelimiters(s string) string {
	s = chatSlideMarkerPattern.ReplaceAllString(s, "")
	s = chatEndSlidePattern.ReplaceAllString(s, "")
	lines := strings.Split(s, "\n")
	for i, line := range lines {
		if strings.HasPrefix(strings.TrimSpace(line), "---") {
			lines[i] = "> " + line
		}
	}
	return strings.Join(lines, "\n")
}

// SanitizeUserInput removes HTML tags, control characters, and pipeline
// delimiter sequences from user text.
func SanitizeUserInput(s string) string {
	s = stripHTML(s)
	s = stripControlChars(s)
	s = neutralizePipelineDelimiters(s)
	return strings.TrimSpace(s)
}

// PostMessageResult is the outcome of POST /chats/:id/messages (async).
type PostMessageResult struct {
	JobID uuid.UUID
}

// PostMessage persists the user message, creates a job, and dispatches work to the worker.
func (s *Service) PostMessage(ctx context.Context, userID, chatID uuid.UUID, rawBody string) (*PostMessageResult, error) {
	if s.worker == nil {
		return nil, ErrWorkerNotConfigured
	}
	chatRow, err := s.getChatIfOwner(ctx, userID, chatID)
	if err != nil {
		return nil, err
	}
	auditText, brandText, err := s.loadAuditBrandTexts(ctx, userID)
	if err != nil {
		return nil, err
	}
	var refKeys []string
	if s.profileSvc != nil {
		refKeys, err = s.profileSvc.ListReferenceS3Keys(ctx, userID)
		if err != nil {
			return nil, err
		}
	}
	body := SanitizeUserInput(rawBody)
	if body == "" {
		return nil, ErrEmptyPrompt
	}
	history, err := s.buildRepromptContext(ctx, chatID)
	if err != nil {
		return nil, err
	}
	userMsg := &db.ChatContent{
		ID:      uuid.New(),
		ChatID:  chatID,
		Role:    db.ChatContentRoleUser,
		Content: body,
	}
	job := &db.Job{
		ID:     uuid.New(),
		ChatID: chatID,
		UserID: userID,
		Status: db.JobStatusProcessing,
	}
	var setTitle *string
	if chatNeedsTitle(chatRow) {
		if preview := titlePreviewFromBody(body); preview != "" {
			setTitle = &preview
		}
	}
	if err := s.repo.CreateUserMessageAndJob(ctx, userMsg, job, setTitle); err != nil {
		return nil, err
	}
	existingHTMLKeys, err := s.latestAssistantHTMLKeys(ctx, chatID)
	if err != nil {
		log.Printf("[chat] latest html keys chat_id=%s err=%v", chatID, err)
		existingHTMLKeys = nil
	}
	payload := jobs.DispatchPayload{
		JobID:                 job.ID,
		UserID:                userID,
		ChatID:                chatID,
		RawMessage:            body,
		AuditText:             auditText,
		BrandText:             brandText,
		RepromptContext:       history,
		ReferenceS3Keys:       refKeys,
		ExistingSlideHTMLKeys: existingHTMLKeys,
	}
	if err := s.worker.DispatchJob(ctx, payload); err != nil {
		msg := err.Error()
		_ = s.jobsRepo.UpdateStatus(ctx, job.ID, db.JobStatusFailed, &msg)
		return nil, ErrWorkerDispatchFailed
	}
	log.Printf("[jobs] dispatch ok job_id=%s chat_id=%s", job.ID, chatID)
	return &PostMessageResult{JobID: job.ID}, nil
}

func (s *Service) buildRepromptContext(ctx context.Context, chatID uuid.UUID) (string, error) {
	res, err := s.repo.GetResumeByChatID(ctx, chatID)
	if err != nil {
		return "", err
	}
	if res != nil && res.Summary != nil && strings.TrimSpace(*res.Summary) != "" {
		return strings.TrimSpace(*res.Summary), nil
	}
	contents, err := s.repo.ListContentsOrdered(ctx, chatID)
	if err != nil {
		return "", err
	}
	var b strings.Builder
	for _, c := range contents {
		b.WriteString(string(c.Role))
		b.WriteString(": ")
		b.WriteString(c.Content)
		b.WriteString("\n")
	}
	return strings.TrimSpace(b.String()), nil
}

// JobStatusView is returned by GET /chats/:id/jobs/:jobId/status.
type JobStatusView struct {
	JobID  uuid.UUID `json:"jobId"`
	Status string    `json:"status"`
	Error  *string   `json:"error"`
}

// GetJobStatus returns job status when the user owns the chat.
func (s *Service) GetJobStatus(ctx context.Context, userID, chatID, jobID uuid.UUID) (*JobStatusView, error) {
	j, err := s.repo.GetJobForChat(ctx, userID, chatID, jobID)
	if ErrRecordNotFound(err) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &JobStatusView{
		JobID:  j.ID,
		Status: string(j.Status),
		Error:  j.ErrorMsg,
	}, nil
}
