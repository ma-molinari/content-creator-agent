package httperr

import (
	"log"
	"net/http"

	"github.com/labstack/echo/v4"
)

// InternalMsg is returned to API clients on unexpected failures (never echo raw errors).
const InternalMsg = "internal error"

// Internal logs the real error and returns a generic 500 for the client.
func Internal(prefix string, err error) *echo.HTTPError {
	if err != nil {
		log.Printf("%s: %v", prefix, err)
	}
	return echo.NewHTTPError(http.StatusInternalServerError, InternalMsg)
}
