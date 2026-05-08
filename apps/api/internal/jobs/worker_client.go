package jobs

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/google/uuid"
)

// DispatchPayload is sent to POST {WORKER_URL}/jobs.
type DispatchPayload struct {
	JobID                 uuid.UUID             `json:"job_id"`
	UserID                uuid.UUID             `json:"user_id"`
	ChatID                uuid.UUID             `json:"chat_id"`
	MessageID             uuid.UUID             `json:"message_id,omitempty"`
	ChatPostType          string                `json:"chat_post_type,omitempty"`
	RawMessage            string                `json:"raw_message"`
	AuditText             string                `json:"audit_text"`
	BrandText             string                `json:"brand_text"`
	ReferenceS3Keys       []string              `json:"reference_s3_keys,omitempty"`
	UserAttachmentS3Keys  []string              `json:"user_attachment_s3_keys,omitempty"`
	UserAttachments       []DispatchAttachment  `json:"user_attachments,omitempty"`
	ExistingSlideHTMLKeys []string              `json:"existing_slide_html_s3_keys,omitempty"`
	ExistingSlideHTML     []DispatchSlideSource `json:"existing_slide_html,omitempty"`
	RequestedSlideCount   *int                  `json:"requested_slide_count,omitempty"`
	// ExpectsSlideRefinement: chat already has a prior assistant JPEG slide artifact;
	// worker must refine from stored HTML keys or surface a refinement error.
	ExpectsSlideRefinement bool `json:"expects_slide_refinement,omitempty"`
}

// DispatchAttachment is richer V2 metadata for a user-uploaded message image.
type DispatchAttachment struct {
	ID        uuid.UUID `json:"id"`
	S3Key     string    `json:"s3_key"`
	MimeType  string    `json:"mime_type"`
	SortOrder int       `json:"sort_order"`
}

// DispatchSlideSource identifies HTML source from the latest assistant turn.
type DispatchSlideSource struct {
	SlideNumber int    `json:"slide_number"`
	HTMLS3Key   string `json:"html_s3_key"`
}

// WorkerClient dispatches async jobs to the Python worker.
type WorkerClient interface {
	DispatchJob(ctx context.Context, payload DispatchPayload) error
}

// Compile-time check.
var _ WorkerClient = (*HTTPWorkerClient)(nil)

// HTTPWorkerClient implements WorkerClient over HTTP.
type HTTPWorkerClient struct {
	baseURL    string
	apiKey     string
	httpClient *http.Client
}

// NewHTTPWorkerClient builds a client. baseURL should be like http://worker:8000 (no trailing slash).
func NewHTTPWorkerClient(baseURL, apiKey string) *HTTPWorkerClient {
	u := strings.TrimRight(strings.TrimSpace(baseURL), "/")
	return &HTTPWorkerClient{
		baseURL: u,
		apiKey:  strings.TrimSpace(apiKey),
		httpClient: &http.Client{
			Timeout: 60 * time.Second,
		},
	}
}

// DispatchJob POSTs to WORKER_URL/jobs with X-Worker-API-Key.
func (c *HTTPWorkerClient) DispatchJob(ctx context.Context, payload DispatchPayload) error {
	if c.baseURL == "" {
		return fmt.Errorf("jobs: worker URL not configured")
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/jobs", bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	if c.apiKey != "" {
		req.Header.Set("X-Worker-API-Key", c.apiKey)
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		log.Printf("[jobs] dispatch request failed job_id=%s err=%v", payload.JobID, err)
		return fmt.Errorf("jobs: dispatch request: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		snip, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
		log.Printf(
			"[jobs] dispatch worker HTTP error job_id=%s status=%d body_snippet=%q",
			payload.JobID,
			resp.StatusCode,
			strings.TrimSpace(string(snip)),
		)
		return fmt.Errorf("jobs: worker returned %s", resp.Status)
	}
	return nil
}
