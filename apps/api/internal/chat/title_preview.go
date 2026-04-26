package chat

import (
	"strings"

	"content-creator-agent/internal/db"
)

const titlePreviewMaxRunes = 80

// titlePreviewFromBody returns a short preview of body for chat title (body must already be sanitized).
func titlePreviewFromBody(body string) string {
	body = strings.TrimSpace(body)
	if body == "" {
		return ""
	}
	runes := []rune(body)
	if len(runes) <= titlePreviewMaxRunes {
		return string(runes)
	}
	return string(runes[:titlePreviewMaxRunes])
}

func chatNeedsTitle(c *db.Chat) bool {
	if c.Title == nil {
		return true
	}
	return strings.TrimSpace(*c.Title) == ""
}
