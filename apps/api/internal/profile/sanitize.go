package profile

import (
	"regexp"
	"strings"
	"unicode"
	"unicode/utf8"
)

const maxProfileTextBytes = 20_000

var (
	profileHTMLTagPattern    = regexp.MustCompile(`<[^>]+>`)
	slideMarkerPattern       = regexp.MustCompile(`(?i)###SLIDE_FILE:[^\n]*`)
	endSlideMarkerPattern    = regexp.MustCompile(`(?i)###END_SLIDE###`)
)

func profileStripHTML(s string) string {
	return profileHTMLTagPattern.ReplaceAllString(s, "")
}

func profileStripControlChars(s string) string {
	return strings.Map(func(r rune) rune {
		if unicode.IsControl(r) && r != '\n' && r != '\t' {
			return -1
		}
		return r
	}, s)
}

// SanitizeProfileText sanitizes audit_text / brand_text before persisting.
// It strips HTML, control characters and pipeline-specific markers, neutralises
// Markdown section headers that could hijack the LLM context, and enforces a
// maximum length of 20 000 bytes.
func SanitizeProfileText(s string) string {
	s = profileStripHTML(s)
	s = profileStripControlChars(s)

	// Remove slide pipeline markers.
	s = slideMarkerPattern.ReplaceAllString(s, "")
	s = endSlideMarkerPattern.ReplaceAllString(s, "")

	// Neutralise Markdown headers that could shadow the ## AUDIT / ## BRAND
	// sections injected by load_profile.py.
	lines := strings.Split(s, "\n")
	for i, line := range lines {
		if strings.HasPrefix(line, "## ") {
			lines[i] = "> " + line
		}
		// Neutralise horizontal rules used as pipeline separators.
		if strings.HasPrefix(strings.TrimSpace(line), "---") {
			lines[i] = "> " + line
		}
	}
	s = strings.Join(lines, "\n")
	s = strings.TrimSpace(s)

	if len(s) > maxProfileTextBytes {
		b := []byte(s)
		b = b[:maxProfileTextBytes]
		// Retreat byte by byte until the slice is valid UTF-8 (at most 3 steps).
		for len(b) > 0 && !utf8.Valid(b) {
			b = b[:len(b)-1]
		}
		s = strings.TrimSpace(string(b))
	}
	return s
}
