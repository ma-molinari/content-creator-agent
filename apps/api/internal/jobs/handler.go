package jobs

import (
	"errors"
	"log"
	"net/http"
	"strings"

	"content-creator-agent/internal/config"
	"content-creator-agent/internal/db"
	"content-creator-agent/internal/storage"

	"github.com/google/uuid"
	"github.com/labstack/echo/v4"
	"gorm.io/gorm"
)

const workerAPIKeyHeader = "X-Worker-API-Key"

// CompleteBody is the worker callback payload.
type CompleteBody struct {
	AssistantText *string `json:"assistantText"`
	Artifacts     []struct {
		S3Key       string `json:"s3Key"`
		SlideNumber int    `json:"slideNumber"`
	} `json:"artifacts"`
	Error *string `json:"error"`
}

// Handler serves internal worker routes.
type Handler struct {
	cfg   *config.Config
	repo  *Repository
	gdb   *gorm.DB
	store storage.StorageService
}

// NewHandler constructs the internal jobs handler.
func NewHandler(cfg *config.Config, repo *Repository, gdb *gorm.DB, store storage.StorageService) *Handler {
	return &Handler{cfg: cfg, repo: repo, gdb: gdb, store: store}
}

// Complete handles POST /internal/jobs/:id/complete.
func (h *Handler) Complete(c echo.Context) error {
	key := strings.TrimSpace(c.Request().Header.Get(workerAPIKeyHeader))
	if h.cfg.WorkerAPIKey == "" || key != h.cfg.WorkerAPIKey {
		return echo.NewHTTPError(http.StatusUnauthorized, "invalid worker API key")
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
	job, err := h.repo.GetByID(ctx, jobID)
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return echo.NewHTTPError(http.StatusNotFound, "job not found")
		}
		return echo.NewHTTPError(http.StatusInternalServerError, err.Error())
	}
	if body.Error != nil && strings.TrimSpace(*body.Error) != "" {
		msg := strings.TrimSpace(*body.Error)
		if err := h.repo.UpdateStatus(ctx, jobID, db.JobStatusFailed, &msg); err != nil {
			return echo.NewHTTPError(http.StatusInternalServerError, err.Error())
		}
		log.Printf("[jobs] complete job_id=%s status=failed error=%s", jobID, msg)
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
		artifacts = append(artifacts, ArtifactRef{S3Key: key, SlideNumber: a.SlideNumber})
	}
	if err := CompleteAssistantReply(ctx, h.gdb, job, assistantText, artifacts, h.store); err != nil {
		if errors.Is(err, gorm.ErrInvalidData) {
			return echo.NewHTTPError(http.StatusBadRequest, "invalid artifact")
		}
		return echo.NewHTTPError(http.StatusInternalServerError, err.Error())
	}
	log.Printf("[jobs] complete job_id=%s status=done", jobID)
	return c.NoContent(http.StatusNoContent)
}
