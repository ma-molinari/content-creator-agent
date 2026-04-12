package chat

import (
	"errors"
	"net/http"
	"time"

	"content-creator-agent/internal/db"
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
	ID          uuid.UUID `json:"id"`
	ChatContentID uuid.UUID `json:"chatContentId"`
	S3Key       string    `json:"s3Key"`
	URL         string    `json:"url"`
	SlideNumber int       `json:"slideNumber"`
	CreatedAt   time.Time `json:"createdAt"`
	UpdatedAt   time.Time `json:"updatedAt"`
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
		return echo.NewHTTPError(http.StatusInternalServerError, err.Error())
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
		return echo.NewHTTPError(http.StatusInternalServerError, err.Error())
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
		return echo.NewHTTPError(http.StatusInternalServerError, err.Error())
	}
}
