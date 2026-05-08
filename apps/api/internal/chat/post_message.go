package chat

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"regexp"
	"strings"
	"sync"
	"unicode"

	"golang.org/x/sync/errgroup"

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

const (
	maxAttachmentBytes       int64 = 5 * 1024 * 1024
	maxAttachmentsPerMessage       = 4
)

var allowedAttachmentMimes = map[string]struct{}{
	"image/jpeg": {}, "image/png": {}, "image/webp": {},
}

// AttachmentInput is one inbound attachment blob before persistence and upload S3 keys.
type AttachmentInput struct {
	Data      []byte
	MimeType  string // sniffed by validateAndUploadAttachments (reserved for multipart metadata)
	SizeBytes int64  // informational; authoritative size is len(Data)
	SortOrder int
}

// duplicated from profile/service.go; keep local for V1 to avoid cross-package coupling.
func extForAttachmentMime(ct string) (string, bool) {
	switch strings.ToLower(ct) {
	case "image/jpeg":
		return ".jpg", true
	case "image/png":
		return ".png", true
	case "image/webp":
		return ".webp", true
	default:
		return "", false
	}
}

func (s *Service) validateAndUploadAttachments(ctx context.Context, userID uuid.UUID, inputs []AttachmentInput) ([]string, []db.ChatContentAttachment, error) {
	if len(inputs) > maxAttachmentsPerMessage {
		return nil, nil, ErrTooManyAttachments
	}
	if len(inputs) == 0 {
		return nil, nil, nil
	}
	for _, inp := range inputs {
		n := len(inp.Data)
		if n == 0 {
			return nil, nil, ErrAttachmentInvalidType
		}
		if int64(n) > maxAttachmentBytes {
			return nil, nil, ErrAttachmentTooLarge
		}
		sniff := http.DetectContentType(inp.Data)
		if _, ok := allowedAttachmentMimes[sniff]; !ok {
			return nil, nil, ErrAttachmentInvalidType
		}
	}

	var mu sync.Mutex
	var rolled []string
	g, egCtx := errgroup.WithContext(ctx)
	keysOut := make([]string, len(inputs))
	attsOut := make([]db.ChatContentAttachment, len(inputs))

	for i := range inputs {
		idx := i
		inp := inputs[idx]
		g.Go(func() error {
			sniff := http.DetectContentType(inp.Data)
			if _, ok := allowedAttachmentMimes[sniff]; !ok {
				return ErrAttachmentInvalidType
			}
			ext, ok := extForAttachmentMime(sniff)
			if !ok {
				return ErrAttachmentInvalidType
			}
			key := fmt.Sprintf("users/%s/chat-attachments/%s%s", userID.String(), uuid.New().String(), ext)
			if err := s.store.Upload(egCtx, key, inp.Data); err != nil {
				return err
			}
			mu.Lock()
			rolled = append(rolled, key)
			mu.Unlock()

			attsOut[idx] = db.ChatContentAttachment{
				ID:        uuid.New(),
				S3Key:     key,
				MimeType:  sniff,
				SizeBytes: int64(len(inp.Data)),
				SortOrder: inp.SortOrder,
			}
			keysOut[idx] = key
			return nil
		})
	}

	if err := g.Wait(); err != nil {
		// Best-effort cleanup; avoid failing delete after failed upload aggregate.
		_ = s.store.DeleteMany(context.Background(), rolled)
		return nil, nil, fmt.Errorf("%w: %w", ErrAttachmentUploadFailed, err)
	}

	return keysOut, attsOut, nil
}

type PostMessageResult struct {
	JobID uuid.UUID
}

// PostMessage persists the user message, creates a job, and dispatches work to the worker.
func (s *Service) PostMessage(ctx context.Context, userID, chatID uuid.UUID, rawBody string, attachments []AttachmentInput) (*PostMessageResult, error) {
	if s.worker == nil {
		return nil, ErrWorkerNotConfigured
	}
	chatRow, err := s.getChatIfOwner(ctx, userID, chatID)
	if err != nil {
		return nil, err
	}
	body := SanitizeUserInput(rawBody)
	if body == "" {
		return nil, ErrEmptyPrompt
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
	var attKeys []string
	var chatAtts []db.ChatContentAttachment
	if len(attachments) > 0 {
		keys, atts, err := s.validateAndUploadAttachments(ctx, userID, attachments)
		if err != nil {
			return nil, err
		}
		attKeys = keys
		chatAtts = atts
	}
	if err := s.repo.CreateUserMessageAndJob(ctx, userMsg, job, setTitle, chatAtts); err != nil {
		return nil, err
	}
	var existingHTMLRefs []AssistantHTMLRef
	if s.latestAssistantHTMLRefs != nil {
		existingHTMLRefs, err = s.latestAssistantHTMLRefs(ctx, chatID)
		if err != nil {
			log.Printf("[chat] latest html refs chat_id=%s err=%v", chatID, err)
			existingHTMLRefs = nil
		}
	}
	existingHTMLKeys := make([]string, 0, len(existingHTMLRefs))
	for _, ref := range existingHTMLRefs {
		if strings.TrimSpace(ref.HTMLS3Key) != "" {
			existingHTMLKeys = append(existingHTMLKeys, ref.HTMLS3Key)
		}
	}
	if len(existingHTMLKeys) == 0 && s.latestAssistantHTMLKeys != nil {
		existingHTMLKeys, err = s.latestAssistantHTMLKeys(ctx, chatID)
		if err != nil {
			log.Printf("[chat] latest html keys chat_id=%s err=%v", chatID, err)
			existingHTMLKeys = nil
		}
		for idx, key := range existingHTMLKeys {
			existingHTMLRefs = append(existingHTMLRefs, AssistantHTMLRef{SlideNumber: idx + 1, HTMLS3Key: key})
		}
	}
	expectsSlideRefinement, err := s.repo.ChatHasAssistantWithSlideArtifacts(ctx, chatID)
	if err != nil {
		log.Printf("[chat] prior slide artifact check chat_id=%s err=%v", chatID, err)
		expectsSlideRefinement = false
	}
	dispatchAttachments := make([]jobs.DispatchAttachment, 0, len(chatAtts))
	for _, att := range chatAtts {
		dispatchAttachments = append(dispatchAttachments, jobs.DispatchAttachment{
			ID:        att.ID,
			S3Key:     att.S3Key,
			MimeType:  att.MimeType,
			SortOrder: att.SortOrder,
		})
	}
	dispatchSlideSources := make([]jobs.DispatchSlideSource, 0, len(existingHTMLRefs))
	for _, ref := range existingHTMLRefs {
		dispatchSlideSources = append(dispatchSlideSources, jobs.DispatchSlideSource{
			SlideNumber: ref.SlideNumber,
			HTMLS3Key:   ref.HTMLS3Key,
		})
	}
	payload := jobs.DispatchPayload{
		JobID:                  job.ID,
		UserID:                 userID,
		ChatID:                 chatID,
		MessageID:              userMsg.ID,
		ChatPostType:           string(chatRow.PostType),
		RawMessage:             body,
		AuditText:              auditText,
		BrandText:              brandText,
		ReferenceS3Keys:        refKeys,
		UserAttachmentS3Keys:   attKeys,
		UserAttachments:        dispatchAttachments,
		ExistingSlideHTMLKeys:  existingHTMLKeys,
		ExistingSlideHTML:      dispatchSlideSources,
		ExpectsSlideRefinement: expectsSlideRefinement,
	}
	if err := s.worker.DispatchJob(ctx, payload); err != nil {
		msg := err.Error()
		if upErr := s.jobsRepo.UpdateStatus(ctx, job.ID, db.JobStatusFailed, &msg); upErr != nil {
			log.Printf("[chat] job mark failed after dispatch error job_id=%s update_err=%v dispatch_err=%v", job.ID, upErr, err)
		}
		return nil, ErrWorkerDispatchFailed
	}
	log.Printf("[jobs] dispatch ok job_id=%s chat_id=%s", job.ID, chatID)
	return &PostMessageResult{JobID: job.ID}, nil
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
