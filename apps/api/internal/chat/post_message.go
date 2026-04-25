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

var htmlTagPattern = regexp.MustCompile(`<[^>]+>`)

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

// SanitizeUserInput removes HTML tags and control characters from user text.
func SanitizeUserInput(s string) string {
	s = stripHTML(s)
	s = stripControlChars(s)
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
	if err := s.assertChatOwner(ctx, userID, chatID); err != nil {
		return nil, err
	}
	ok, err := s.IsProfileConfigured(ctx, userID)
	if err != nil {
		return nil, err
	}
	if !ok {
		return nil, ErrSetupRequired
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
		Status: db.JobStatusPending,
	}
	if err := s.repo.CreateUserMessageAndJob(ctx, userMsg, job); err != nil {
		return nil, err
	}
	payload := jobs.DispatchPayload{
		JobID:             job.ID,
		UserID:            userID,
		ChatID:            chatID,
		RawMessage:        body,
		AuditText:         auditText,
		BrandText:         brandText,
		RepromptContext:   history,
		ReferenceS3Keys:   refKeys,
	}
	if err := s.worker.DispatchJob(ctx, payload); err != nil {
		msg := err.Error()
		_ = s.jobsRepo.UpdateStatus(ctx, job.ID, db.JobStatusFailed, &msg)
		return nil, ErrWorkerDispatchFailed
	}
	log.Printf("[jobs] dispatch job_id=%s chat_id=%s user_id=%s", job.ID, chatID, userID)
	if err := s.jobsRepo.UpdateStatus(ctx, job.ID, db.JobStatusProcessing, nil); err != nil {
		return nil, err
	}
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
