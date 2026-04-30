package middleware

import (
	"net/http"
	"time"

	"github.com/google/uuid"
	"github.com/labstack/echo/v4"
	"github.com/ulule/limiter/v3"
	"github.com/ulule/limiter/v3/drivers/store/memory"
)

// AuthByIP limits requests per client IP (20 per 5 minutes). Apply to /auth/* routes.
func AuthByIP() echo.MiddlewareFunc {
	rate := limiter.Rate{
		Period: 5 * time.Minute,
		Limit:  20,
	}
	store := memory.NewStore()
	instance := limiter.New(store, rate)
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			ip := c.RealIP()
			ctx, err := instance.Get(c.Request().Context(), ip)
			if err != nil {
				return echo.NewHTTPError(http.StatusInternalServerError, "rate limiter error")
			}
			if ctx.Reached {
				return echo.NewHTTPError(http.StatusTooManyRequests, "too many requests")
			}
			return next(c)
		}
	}
}

// LLMByUser limits authenticated LLM-style endpoints per user (20 per minute). Requires JWT middleware before it.
func LLMByUser() echo.MiddlewareFunc {
	rate := limiter.Rate{
		Period: 1 * time.Minute,
		Limit:  20,
	}
	store := memory.NewStore()
	instance := limiter.New(store, rate)
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			uid := UserID(c)
			if uid == uuid.Nil {
				return echo.NewHTTPError(http.StatusUnauthorized, "unauthorized")
			}
			key := uid.String()
			ctx, err := instance.Get(c.Request().Context(), key)
			if err != nil {
				return echo.NewHTTPError(http.StatusInternalServerError, "rate limiter error")
			}
			if ctx.Reached {
				return echo.NewHTTPError(http.StatusTooManyRequests, "too many requests")
			}
			return next(c)
		}
	}
}
