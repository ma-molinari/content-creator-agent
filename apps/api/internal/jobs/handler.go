package jobs

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strings"

	"content-creator-agent/internal/config"
	"content-creator-agent/internal/httperr"
	"content-creator-agent/internal/storage"

	"github.com/google/uuid"
	"github.com/labstack/echo/v4"
	"gorm.io/gorm"
)

const workerAPIKeyHeader = "X-Worker-API-Key"

// CompleteBody is the worker callback payload.
type CompleteBody struct {
	Structured    *StructuredArtifact `json:"structured,omitempty"`
	AssistantText *string             `json:"assistantText"`
	Artifacts     []struct {
		S3Key       string  `json:"s3Key"`
		SlideNumber int     `json:"slideNumber"`
		HTMLS3Key   *string `json:"htmlS3Key,omitempty"`
	} `json:"artifacts"`
	Error          *string          `json:"error"`
	ErrorCode      *string          `json:"errorCode,omitempty"`
	WorkerMetadata *json.RawMessage `json:"workerMetadata,omitempty"`
}

// ProgressBody is sent by the worker while a job is processing.
type ProgressBody struct {
	Stage     string  `json:"stage"`
	Progress  int     `json:"progress"`
	ErrorCode *string `json:"errorCode,omitempty"`
}

// Handler serves internal worker routes.
type Handler struct {
	cfg   *config.Config
	gdb   *gorm.DB
	store storage.StorageService
}

// NewHandler constructs the internal jobs handler.
func NewHandler(cfg *config.Config, gdb *gorm.DB, store storage.StorageService) *Handler {
	return &Handler{cfg: cfg, gdb: gdb, store: store}
}

func (h *Handler) requireWorker(c echo.Context) *echo.HTTPError {
	key := strings.TrimSpace(c.Request().Header.Get(workerAPIKeyHeader))
	if h.cfg.WorkerAPIKey == "" || key != h.cfg.WorkerAPIKey {
		return echo.NewHTTPError(http.StatusUnauthorized, "invalid worker API key")
	}
	return nil
}

// Complete handles POST /internal/jobs/:id/complete.
func (h *Handler) Complete(c echo.Context) error {
	if err := h.requireWorker(c); err != nil {
		return err
	}
	jobID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid job id")
	}
	var body CompleteBody
	if err := c.Bind(&body); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid JSON body")
	}
	ctx := c.Request().Context()
	if body.Error != nil && strings.TrimSpace(*body.Error) != "" {
		msg := strings.TrimSpace(*body.Error)
		noop, err := ApplyWorkerFailureWithCode(ctx, h.gdb, jobID, msg, body.ErrorCode, body.WorkerMetadata)
		if err != nil {
			if errors.Is(err, gorm.ErrRecordNotFound) {
				return echo.NewHTTPError(http.StatusNotFound, "job not found")
			}
			return httperr.Internal("[jobs] complete apply worker failure", err)
		}
		if noop {
			log.Printf("[jobs] complete job_id=%s worker error ignored (terminal state)", jobID)
		} else {
			logJobOutcome(ctx, h.gdb, jobID, "failed", metricErrorCode(body.ErrorCode))
		}
		return c.NoContent(http.StatusNoContent)
	}
	if body.AssistantText == nil || strings.TrimSpace(*body.AssistantText) == "" {
		return echo.NewHTTPError(http.StatusBadRequest, "assistantText is required when error is not set")
	}
	assistantText := strings.TrimSpace(*body.AssistantText)
	artifacts := make([]ArtifactRef, 0, len(body.Artifacts))
	for _, a := range body.Artifacts {
		key := strings.TrimSpace(a.S3Key)
		if key == "" {
			return echo.NewHTTPError(http.StatusBadRequest, "each artifact must include s3Key")
		}
		artifacts = append(artifacts, ArtifactRef{S3Key: key, SlideNumber: a.SlideNumber, HtmlS3Key: a.HTMLS3Key})
	}
	if body.Structured != nil {
		alreadyDone, conflict, err := CompleteStructuredReply(ctx, h.gdb, jobID, assistantText, artifacts, *body.Structured, h.store)
		if err != nil {
			if errors.Is(err, gorm.ErrRecordNotFound) {
				return echo.NewHTTPError(http.StatusNotFound, "job not found")
			}
			if errors.Is(err, ErrJobCompleteConflict) {
				return echo.NewHTTPError(http.StatusConflict, "job already failed")
			}
			if errors.Is(err, ErrJobNotProcessing) || errors.Is(err, gorm.ErrInvalidData) || errors.Is(err, ErrInvalidSlideS3Key) || errors.Is(err, ErrArtifactObjectNotFound) {
				return echo.NewHTTPError(http.StatusBadRequest, "invalid structured completion")
			}
			return httperr.Internal("[jobs] structured complete", err)
		}
		if conflict {
			logJobOutcome(ctx, h.gdb, jobID, "conflict", "VERSION_CONFLICT")
			return c.JSON(http.StatusConflict, map[string]string{"code": "VERSION_CONFLICT"})
		}
		if alreadyDone {
			log.Printf("[jobs] structured complete job_id=%s status=done (idempotent no-op)", jobID)
		} else {
			logJobOutcome(ctx, h.gdb, jobID, "done", "NONE")
		}
		return c.NoContent(http.StatusNoContent)
	}
	alreadyDone, err := CompleteAssistantReply(ctx, h.gdb, jobID, assistantText, artifacts, h.store, body.WorkerMetadata)
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return echo.NewHTTPError(http.StatusNotFound, "job not found")
		}
		if errors.Is(err, ErrJobCompleteConflict) {
			return echo.NewHTTPError(http.StatusConflict, "job already failed")
		}
		if errors.Is(err, ErrJobNotProcessing) {
			return echo.NewHTTPError(http.StatusBadRequest, "job not in processing state")
		}
		if errors.Is(err, gorm.ErrInvalidData) {
			return echo.NewHTTPError(http.StatusBadRequest, "invalid artifact")
		}
		if errors.Is(err, ErrInvalidSlideS3Key) {
			return echo.NewHTTPError(http.StatusBadRequest, "invalid s3Key")
		}
		if errors.Is(err, ErrArtifactObjectNotFound) {
			return echo.NewHTTPError(http.StatusBadRequest, map[string]string{
				"message": "Artefato não existe no bucket configurado na API (confira AWS_S3_BUCKET, região e credenciais alinhados ao worker).",
			})
		}
		return httperr.Internal("[jobs] complete persist", err)
	}
	if alreadyDone {
		log.Printf("[jobs] complete job_id=%s status=done (idempotent no-op)", jobID)
	} else {
		logJobOutcome(ctx, h.gdb, jobID, "done", "NONE")
	}
	return c.NoContent(http.StatusNoContent)
}

// Progress handles POST /internal/jobs/:id/progress.
func (h *Handler) Progress(c echo.Context) error {
	if err := h.requireWorker(c); err != nil {
		return err
	}
	jobID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid job id")
	}
	var body ProgressBody
	if err := c.Bind(&body); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid JSON body")
	}
	if strings.TrimSpace(body.Stage) == "" {
		return echo.NewHTTPError(http.StatusBadRequest, "stage is required")
	}
	repo := NewRepository(h.gdb)
	if err := repo.UpdateProgress(c.Request().Context(), jobID, body.Stage, body.Progress, body.ErrorCode); err != nil {
		return httperr.Internal("[jobs] progress update", err)
	}
	return c.NoContent(http.StatusNoContent)
}
