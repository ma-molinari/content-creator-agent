package middleware

import (
	"net/http"
	"strings"

	"github.com/labstack/echo/v4"
)

// SecurityHeaders sets standard hardening headers.
// HSTS is only emitted when httpsOnly is true to avoid breaking local dev over HTTP.
func SecurityHeaders(httpsOnly bool) echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			c.Response().Header().Set("X-Content-Type-Options", "nosniff")
			c.Response().Header().Set("X-Frame-Options", "DENY")
			c.Response().Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
			c.Response().Header().Set("Content-Security-Policy", "default-src 'none'")
			if httpsOnly {
				c.Response().Header().Set("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
			}
			c.Response().Header().Set("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
			return next(c)
		}
	}
}

// CORS restricts origins to an allowlist. Empty allowlist disables CORS headers (same-origin only).
func CORS(allowedOrigins []string) echo.MiddlewareFunc {
	allow := make(map[string]struct{}, len(allowedOrigins))
	for _, o := range allowedOrigins {
		o = strings.TrimSpace(o)
		if o != "" {
			allow[o] = struct{}{}
		}
	}
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			c.Response().Header().Add("Vary", "Origin")
			origin := c.Request().Header.Get("Origin")
			if origin != "" {
				if _, ok := allow[origin]; ok {
					c.Response().Header().Set("Access-Control-Allow-Origin", origin)
					c.Response().Header().Set("Access-Control-Allow-Credentials", "true")
					c.Response().Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
					c.Response().Header().Set("Access-Control-Allow-Headers", "Authorization, Content-Type, Origin")
					c.Response().Header().Set("Access-Control-Max-Age", "86400")
					if c.Request().Method == http.MethodOptions {
						return c.NoContent(http.StatusNoContent)
					}
				} else if c.Request().Method == http.MethodOptions {
					return echo.NewHTTPError(http.StatusForbidden, "origin not allowed")
				}
			}
			return next(c)
		}
	}
}
