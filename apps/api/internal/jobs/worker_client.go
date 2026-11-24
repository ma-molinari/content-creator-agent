package jobs

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/google/uuid"
)

// ErrDispatchOutcomeUnknown means the worker might have accepted the job.
var ErrDispatchOutcomeUnknown = errors.New("worker dispatch outcome unknown")

// DispatchPayload is sent to POST {WORKER_URL}/jobs.
type DispatchPayload struct {
	AuthorizedAssetSources map[string]string     `json:"authorized_asset_sources,omitempty"`
	ReferenceAssetSources  map[string]string     `json:"reference_asset_sources"`
	PostFormat             string                `json:"post_format,omitempty"`
	TargetSchemaVersion    *int                  `json:"target_schema_version,omitempty"`
	GenerationMode         string                `json:"generation_mode,omitempty"`
	BaseVersionID          *uuid.UUID            `json:"base_version_id,omitempty"`
	DocumentS3Key          string                `json:"document_s3_key,omitempty"`
	JobID                  uuid.UUID             `json:"job_id"`
	UserID                 uuid.UUID             `json:"user_id"`
	ChatID                 uuid.UUID             `json:"chat_id"`
	MessageID              uuid.UUID             `json:"message_id,omitempty"`
	ChatPostType           string                `json:"chat_post_type,omitempty"`
	RawMessage             string                `json:"raw_message"`
	AuditText              string                `json:"audit_text"`
	BrandText              string                `json:"brand_text"`
	ReferenceS3Keys        []string              `json:"reference_s3_keys,omitempty"`
	UserAttachmentS3Keys   []string              `json:"user_attachment_s3_keys,omitempty"`
	UserAttachments        []DispatchAttachment  `json:"user_attachments,omitempty"`
	KnownAttachments       []DispatchAttachment  `json:"known_attachments,omitempty"`
	ExistingSlideHTMLKeys  []string              `json:"existing_slide_html_s3_keys,omitempty"`
	ExistingSlideHTML      []DispatchSlideSource `json:"existing_slide_html,omitempty"`
	RequestedSlideCount    *int                  `json:"requested_slide_count,omitempty"`
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
	if payload.TargetSchemaVersion != nil && (*payload.TargetSchemaVersion < 1 || *payload.TargetSchemaVersion > 3 || (*payload.TargetSchemaVersion > 1 && payload.PostFormat != "structured_v1")) {
		return fmt.Errorf("jobs: invalid target schema")
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	path := "/jobs"
	if payload.PostFormat == "structured_v1" {
		path = "/jobs/structured"
		if payload.TargetSchemaVersion != nil && *payload.TargetSchemaVersion == 2 {
			path = "/jobs/structured/v2"
		} else if payload.TargetSchemaVersion != nil && *payload.TargetSchemaVersion == 3 {
			path = "/jobs/structured/v3"
		}
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+path, bytes.NewReader(body))
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
		return fmt.Errorf("%w: %v", ErrDispatchOutcomeUnknown, err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		snip, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
		if payload.TargetSchemaVersion != nil && *payload.TargetSchemaVersion >= 2 {
			log.Printf("[jobs] dispatch worker HTTP error job_id=%s status=%d", payload.JobID, resp.StatusCode)
		} else {
			log.Printf(
				"[jobs] dispatch worker HTTP error job_id=%s status=%d body_snippet=%q",
				payload.JobID,
				resp.StatusCode,
				strings.TrimSpace(string(snip)),
			)
		}
		if resp.StatusCode >= 500 {
			return fmt.Errorf("%w: worker returned %s", ErrDispatchOutcomeUnknown, resp.Status)
		}
		return fmt.Errorf("jobs: worker returned %s", resp.Status)
	}
	return nil
}

// SupportsStructured reports capability only when a worker explicitly advertises contract V1.
func (c *HTTPWorkerClient) SupportsStructured(ctx context.Context) bool {
	capability, ok := c.structuredCapability(ctx)
	return ok && capability.ContractVersion == 1
}

type structuredCapability struct {
	ContractVersion         int   `json:"contractVersion"`
	ReadSchemas             []int `json:"readSchemas"`
	WriteSchemas            []int `json:"writeSchemas"`
	DecorationOperations    bool  `json:"decorationOperations"`
	ReferencePolicyVersion  int   `json:"referencePolicyVersion"`
	StockImageOperations    bool  `json:"stockImageOperations"`
	ImageCompositionVersion int   `json:"imageCompositionVersion"`
}

func (c *HTTPWorkerClient) structuredCapability(ctx context.Context) (structuredCapability, bool) {
	var none structuredCapability
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.baseURL+"/capabilities", nil)
	if err != nil {
		return none, false
	}
	req.Header.Set("X-Worker-API-Key", c.apiKey)
	response, err := c.httpClient.Do(req)
	if err != nil {
		return none, false
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return none, false
	}
	var body struct {
		StructuredPost structuredCapability `json:"structuredPost"`
	}
	if err := json.NewDecoder(io.LimitReader(response.Body, 4096)).Decode(&body); err != nil {
		return none, false
	}
	return body.StructuredPost, true
}

// SupportsStructuredV2 requires write V2 and, for edits, the exact base read schema.
// readSchema=0 denotes a creation without a base.
func (c *HTTPWorkerClient) SupportsStructuredV2(ctx context.Context, readSchema int) bool {
	capability, ok := c.structuredCapability(ctx)
	if !ok || capability.ContractVersion != 1 || !capability.DecorationOperations || !containsSchema(capability.WriteSchemas, 2) {
		return false
	}
	return readSchema == 0 || ((readSchema == 1 || readSchema == 2) && containsSchema(capability.ReadSchemas, readSchema))
}

func (c *HTTPWorkerClient) SupportsStructuredV3(ctx context.Context, readSchema int) bool {
	capability, ok := c.structuredCapability(ctx)
	if !ok || capability.ContractVersion != 1 || !capability.StockImageOperations || capability.ImageCompositionVersion != 2 || !capability.DecorationOperations || !containsSchema(capability.WriteSchemas, 3) {
		return false
	}
	return readSchema == 0 || ((readSchema >= 1 && readSchema <= 3) && containsSchema(capability.ReadSchemas, readSchema))
}

func containsSchema(versions []int, wanted int) bool {
	for _, version := range versions {
		if version == wanted {
			return true
		}
	}
	return false
}

func (c *HTTPWorkerClient) SupportsReferencePolicy(ctx context.Context) bool {
	capability, ok := c.structuredCapability(ctx)
	return ok && capability.ContractVersion == 1 && capability.ReferencePolicyVersion == 1
}
