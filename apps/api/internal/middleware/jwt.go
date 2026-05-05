package middleware

import (
	"fmt"
	"net/http"
	"strings"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/labstack/echo/v4"
)

// UserIDKey is the Echo context key for the authenticated user's UUID.
const UserIDKey = "user_id"

// JWT validates Authorization: Bearer <access token> and stores user UUID in context.
func JWT(secret string) echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			auth := c.Request().Header.Get("Authorization")
			if auth == "" || !strings.HasPrefix(auth, "Bearer ") {
				return echo.NewHTTPError(http.StatusUnauthorized, "missing or invalid authorization")
			}
			raw := strings.TrimPrefix(auth, "Bearer ")
			parser := jwt.NewParser(jwt.WithValidMethods([]string{jwt.SigningMethodHS256.Alg()}))
			tok, err := parser.ParseWithClaims(raw, &jwt.RegisteredClaims{}, func(t *jwt.Token) (interface{}, error) {
				if t.Method != jwt.SigningMethodHS256 {
					return nil, fmt.Errorf("invalid signing method")
				}
				return []byte(secret), nil
			})
			if err != nil || !tok.Valid {
				return echo.NewHTTPError(http.StatusUnauthorized, "invalid or expired token")
			}
			claims, ok := tok.Claims.(*jwt.RegisteredClaims)
			if !ok || claims.Subject == "" {
				return echo.NewHTTPError(http.StatusUnauthorized, "invalid token")
			}
			uid, err := uuid.Parse(claims.Subject)
			if err != nil {
				return echo.NewHTTPError(http.StatusUnauthorized, "invalid token")
			}
			c.Set(UserIDKey, uid)
			return next(c)
		}
	}
}

// UserID returns the authenticated user id or uuid.Nil if unset.
func UserID(c echo.Context) uuid.UUID {
	v := c.Get(UserIDKey)
	id, ok := v.(uuid.UUID)
	if !ok {
		return uuid.Nil
	}
	return id
}
