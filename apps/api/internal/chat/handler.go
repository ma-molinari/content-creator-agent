package chat

import (
	"errors"
	"net/http"
	"time"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/httperr"
	"content-creator-agent/internal/middleware"

	"github.com/google/uuid"
	"github.com/labstack/echo/v4"
)

// Handler exposes chat HTTP endpoints.
type Handler struct {
	svc *Service
}

// NewHandler constructs a chat handler.
func NewHandler(svc *Service) *Handler {
	return &Handler{svc: svc}
}

type chatJSON struct {
	ID        uuid.UUID         `json:"id"`
	UserID    uuid.UUID         `json:"userId"`
	PostType  string            `json:"postType"`
	Title     *string           `json:"title,omitempty"`
	CreatedAt time.Time         `json:"createdAt"`
	UpdatedAt time.Time         `json:"updatedAt"`
	Contents  []chatContentJSON `json:"contents,omitempty"`
}

type chatContentJSON struct {
	ID        uuid.UUID            `json:"id"`
	ChatID    uuid.UUID            `json:"chatId"`
	Role      string               `json:"role"`
	Content   string               `json:"content"`
	CreatedAt time.Time            `json:"createdAt"`
	UpdatedAt time.Time            `json:"updatedAt"`
	Images    []chatContentImgJSON `json:"images,omitempty"`
}

type chatContentImgJSON struct {
	ID            uuid.UUID `json:"id"`
	ChatContentID uuid.UUID `json:"chatContentId"`
	S3Key         string    `json:"s3Key"`
	URL           string    `json:"url"`
	SlideNumber   int       `json:"slideNumber"`
	CreatedAt     time.Time `json:"createdAt"`
	UpdatedAt     time.Time `json:"updatedAt"`
}

func chatToJSON(c *db.Chat) chatJSON {
	out := chatJSON{
		ID:        c.ID,
		UserID:    c.UserID,
		PostType:  string(c.PostType),
		Title:     c.Title,
		CreatedAt: c.CreatedAt,
		UpdatedAt: c.UpdatedAt,
	}
	for _, row := range c.Contents {
		item := chatContentJSON{
			ID:        row.ID,
			ChatID:    row.ChatID,
			Role:      string(row.Role),
			Content:   row.Content,
			CreatedAt: row.CreatedAt,
			UpdatedAt: row.UpdatedAt,
		}
		for _, im := range row.Images {
			item.Images = append(item.Images, chatContentImgJSON{
				ID:            im.ID,
				ChatContentID: im.ChatContentID,
				S3Key:         im.S3Key,
				URL:           im.URL,
				SlideNumber:   im.SlideNumber,
				CreatedAt:     im.CreatedAt,
				UpdatedAt:     im.UpdatedAt,
			})
		}
		out.Contents = append(out.Contents, item)
	}
	return out
}

// ListChats handles GET /chats.
func (h *Handler) ListChats(c echo.Context) error {
	uid := middleware.UserID(c)
	list, err := h.svc.ListChats(c.Request().Context(), uid)
	if err != nil {
		return httperr.Internal("[chat] list chats", err)
	}
	out := make([]chatJSON, 0, len(list))
	for i := range list {
		out = append(out, chatToJSON(&list[i]))
	}
	return c.JSON(http.StatusOK, out)
}

type createChatBody struct {
	PostType string `json:"postType"`
}

// CreateChat handles POST /chats.
func (h *Handler) CreateChat(c echo.Context) error {
	var body createChatBody
	if err := c.Bind(&body); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid JSON body")
	}
	uid := middleware.UserID(c)
	chat, err := h.svc.CreateChat(c.Request().Context(), uid, body.PostType)
	if err != nil {
		if errors.Is(err, ErrBadPostType) {
			return echo.NewHTTPError(http.StatusBadRequest, "invalid postType")
		}
		return httperr.Internal("[chat] create chat", err)
	}
	return c.JSON(http.StatusCreated, chatToJSON(chat))
}

// GetChat handles GET /chats/:id.
func (h *Handler) GetChat(c echo.Context) error {
	chatID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid chat id")
	}
	uid := middleware.UserID(c)
	chat, err := h.svc.GetChat(c.Request().Context(), uid, chatID)
	if err != nil {
		return mapChatErr(err)
	}
	return c.JSON(http.StatusOK, chatToJSON(chat))
}

// DeleteChat handles DELETE /chats/:id.
func (h *Handler) DeleteChat(c echo.Context) error {
	chatID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid chat id")
	}
	uid := middleware.UserID(c)
	if err := h.svc.DeleteChat(c.Request().Context(), uid, chatID); err != nil {
		return mapChatErr(err)
	}
	return c.NoContent(http.StatusNoContent)
}

// ListFiles handles GET /chats/:id/files.
func (h *Handler) ListFiles(c echo.Context) error {
	chatID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid chat id")
	}
	uid := middleware.UserID(c)
	items, err := h.svc.ListFiles(c.Request().Context(), uid, chatID)
	if err != nil {
		return mapChatErr(err)
	}
	return c.JSON(http.StatusOK, items)
}

// DownloadZip handles GET /chats/:id/files/download.
func (h *Handler) DownloadZip(c echo.Context) error {
	chatID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid chat id")
	}
	uid := middleware.UserID(c)
	data, filename, err := h.svc.BuildChatZip(c.Request().Context(), uid, chatID)
	if err != nil {
		if errors.Is(err, ErrNoFiles) {
			return echo.NewHTTPError(http.StatusNotFound, "no files")
		}
		return mapChatErr(err)
	}
	c.Response().Header().Set(echo.HeaderContentType, "application/zip")
	c.Response().Header().Set(echo.HeaderContentDisposition, `attachment; filename="`+filename+`"`)
	return c.Blob(http.StatusOK, "application/zip", data)
}

// GetFile handles GET /chats/:id/files/:fileId.
func (h *Handler) GetFile(c echo.Context) error {
	chatID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid chat id")
	}
	fileID, err := uuid.Parse(c.Param("fileId"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid file id")
	}
	uid := middleware.UserID(c)
	data, err := h.svc.GetImageJPEG(c.Request().Context(), uid, chatID, fileID)
	if err != nil {
		return mapChatErr(err)
	}
	return c.Blob(http.StatusOK, "image/jpeg", data)
}

func mapChatErr(err error) *echo.HTTPError {
	switch {
	case errors.Is(err, ErrNotFound):
		return echo.NewHTTPError(http.StatusNotFound, "not found")
	case errors.Is(err, ErrForbidden):
		return echo.NewHTTPError(http.StatusForbidden, "forbidden")
	default:
		return httperr.Internal("[chat] mapChatErr", err)
	}
}

type postMessageBody struct {
	Content string `json:"content"`
}

type postMessageAccepted struct {
	JobID uuid.UUID `json:"jobId"`
}

// PostMessage handles POST /chats/:id/messages (with LLM rate limit middleware).
func (h *Handler) PostMessage(c echo.Context) error {
	chatID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid chat id")
	}
	var body postMessageBody
	if err := c.Bind(&body); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid JSON body")
	}
	if body.Content == "" {
		return echo.NewHTTPError(http.StatusBadRequest, "content is required")
	}
	uid := middleware.UserID(c)
	res, err := h.svc.PostMessage(c.Request().Context(), uid, chatID, body.Content)
	if err != nil {
		return mapPostErr(err)
	}
	return c.JSON(http.StatusAccepted, postMessageAccepted{JobID: res.JobID})
}

// GetJobStatus handles GET /chats/:id/jobs/:jobId/status.
func (h *Handler) GetJobStatus(c echo.Context) error {
	chatID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid chat id")
	}
	jobID, err := uuid.Parse(c.Param("jobId"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid job id")
	}
	uid := middleware.UserID(c)
	view, err := h.svc.GetJobStatus(c.Request().Context(), uid, chatID, jobID)
	if err != nil {
		return mapChatErr(err)
	}
	return c.JSON(http.StatusOK, view)
}

// SetupStatus handles GET /setup/status.
func (h *Handler) SetupStatus(c echo.Context) error {
	uid := middleware.UserID(c)
	ok, err := h.svc.IsProfileConfigured(c.Request().Context(), uid)
	if err != nil {
		return httperr.Internal("[chat] setup status", err)
	}
	return c.JSON(http.StatusOK, map[string]bool{"configured": ok})
}

func mapPostErr(err error) *echo.HTTPError {
	switch {
	case errors.Is(err, ErrSetupRequired):
		return echo.NewHTTPError(http.StatusBadRequest, map[string]string{
			"code":    "SETUP_REQUIRED",
			"message": "Preencha o texto de auditoria e de marca em Perfil (PUT /profile) antes de enviar mensagens. Referências de design usam S3 via a mesma área de perfil.",
		})
	case errors.Is(err, ErrWorkerNotConfigured):
		return echo.NewHTTPError(http.StatusServiceUnavailable, "async generation is not configured on this server")
	case errors.Is(err, ErrWorkerDispatchFailed):
		return echo.NewHTTPError(http.StatusBadGateway, "could not reach worker; job marked failed")
	case errors.Is(err, ErrEmptyPrompt):
		return echo.NewHTTPError(http.StatusBadRequest, "content is empty after sanitization")
	}
	if errors.Is(err, ErrNotFound) || errors.Is(err, ErrForbidden) {
		return mapChatErr(err)
	}
	return httperr.Internal("[chat] post message", err)
}
