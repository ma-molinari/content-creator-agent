package profile

import (
	"errors"
	"io"
	"net/http"
	"strings"

	"content-creator-agent/internal/middleware"

	"github.com/google/uuid"
	"github.com/labstack/echo/v4"
)

// Handler exposes profile HTTP endpoints.
type Handler struct {
	svc *Service
}

// NewHandler constructs a profile handler.
func NewHandler(svc *Service) *Handler {
	return &Handler{svc: svc}
}

type saveBody struct {
	AuditText string `json:"auditText"`
	BrandText string `json:"brandText"`
}

// Get handles GET /profile.
func (h *Handler) Get(c echo.Context) error {
	uid := middleware.UserID(c)
	v, err := h.svc.GetProfile(c.Request().Context(), uid)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, err.Error())
	}
	return c.JSON(http.StatusOK, v)
}

// Save handles PUT /profile.
func (h *Handler) Save(c echo.Context) error {
	var body saveBody
	if err := c.Bind(&body); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid JSON body")
	}
	uid := middleware.UserID(c)
	if err := h.svc.SaveProfile(c.Request().Context(), uid, body.AuditText, body.BrandText); err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, err.Error())
	}
	v, err := h.svc.GetProfile(c.Request().Context(), uid)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, err.Error())
	}
	return c.JSON(http.StatusOK, v)
}

// PostReference handles POST /profile/references (multipart form, field "file").
func (h *Handler) PostReference(c echo.Context) error {
	uid := middleware.UserID(c)
	file, err := c.FormFile("file")
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "missing or invalid file field (use \"file\")")
	}
	mimeHeader := file.Header
	f, err := file.Open()
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "could not read upload")
	}
	defer f.Close()
	maxB := h.svc.MaxReferenceBytes()
	data, err := io.ReadAll(io.LimitReader(f, maxB+1))
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, err.Error())
	}
	ct := ""
	if v := mimeHeader["Content-Type"]; len(v) > 0 {
		ct = v[0]
	}
	ferr := h.svc.UploadReferenceImage(c.Request().Context(), uid, data, file.Filename, ct)
	if mapProfileRefErr(c, ferr) {
		return nil
	}
	if ferr != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, ferr.Error())
	}
	v, err := h.svc.GetProfile(c.Request().Context(), uid)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, err.Error())
	}
	return c.JSON(http.StatusOK, v)
}

// DeleteReference handles DELETE /profile/references/:id.
func (h *Handler) DeleteReference(c echo.Context) error {
	uid := middleware.UserID(c)
	id, err := uuid.Parse(strings.TrimSpace(c.Param("id")))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid id")
	}
	ferr := h.svc.DeleteReference(c.Request().Context(), uid, id)
	if mapProfileRefErr(c, ferr) {
		return nil
	}
	if ferr != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, ferr.Error())
	}
	return c.NoContent(http.StatusNoContent)
}

func mapProfileRefErr(c echo.Context, err error) bool {
	if err == nil {
		return false
	}
	switch {
	case errors.Is(err, ErrTooManyProfileRefs):
		_ = c.JSON(http.StatusBadRequest, map[string]string{"error": err.Error()})
		return true
	case errors.Is(err, ErrFileTooLarge):
		_ = c.JSON(http.StatusRequestEntityTooLarge, map[string]string{"error": err.Error()})
		return true
	case errors.Is(err, ErrInvalidImageType):
		_ = c.JSON(http.StatusBadRequest, map[string]string{"error": err.Error()})
		return true
	case errors.Is(err, ErrReferenceNotFound):
		_ = c.JSON(http.StatusNotFound, map[string]string{"error": err.Error()})
		return true
	case errors.Is(err, ErrProfileRefsNotAvailable):
		_ = c.JSON(http.StatusServiceUnavailable, map[string]string{"error": "design references unavailable"})
		return true
	default:
		return false
	}
}
