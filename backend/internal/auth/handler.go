package auth

import (
	"errors"
	"net/http"
	"strings"

	"github.com/labstack/echo/v4"
)

const refreshCookieName = "refresh_token"

// Handler exposes auth HTTP handlers.
type Handler struct {
	svc *Service
}

func NewHandler(svc *Service) *Handler {
	return &Handler{svc: svc}
}

type registerBody struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type registerResponse struct {
	SecurityKey string `json:"securityKey"`
}

func (h *Handler) Register(c echo.Context) error {
	var body registerBody
	if err := c.Bind(&body); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid JSON body")
	}
	res, err := h.svc.Register(c.Request().Context(), body.Email, body.Password)
	if err != nil {
		return mapAuthError(err)
	}
	return c.JSON(http.StatusCreated, registerResponse{SecurityKey: res.SecurityKey})
}

type loginBody struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type loginResponse struct {
	AccessToken string `json:"accessToken"`
}

func (h *Handler) Login(c echo.Context) error {
	var body loginBody
	if err := c.Bind(&body); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid JSON body")
	}
	res, err := h.svc.Login(c.Request().Context(), body.Email, body.Password)
	if err != nil {
		return mapAuthError(err)
	}
	cookie := &http.Cookie{
		Name:     refreshCookieName,
		Value:    res.RefreshToken,
		Path:     "/",
		MaxAge:   7 * 24 * 3600,
		HttpOnly: true,
		Secure:   h.svc.CookieSecure(),
		SameSite: http.SameSiteStrictMode,
	}
	c.SetCookie(cookie)
	return c.JSON(http.StatusOK, loginResponse{AccessToken: res.AccessToken})
}
func mapAuthError(err error) error {
	var se *ServiceError
	if errors.As(err, &se) {
		return echo.NewHTTPError(se.HTTPStatus, se.Message)
	}
	return echo.NewHTTPError(http.StatusInternalServerError, "internal error")
}
