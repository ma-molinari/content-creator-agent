package jobs

import (
	"bytes"
	"encoding/json"
	"io"
	"regexp"
	"strings"
	"unicode/utf8"

	"content-creator-agent/internal/db"
	"gorm.io/gorm"
)

var structuredID = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`)
var structuredColor = regexp.MustCompile(`^#[0-9a-fA-F]{6}$`)
var structuredUnsafeText = regexp.MustCompile(`(?i)<\s*/?\s*[a-zA-Z!][^>]*>|(?:https?://|www\.)`)

func decodeStructured(data []byte, dst interface{}) error {
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(dst); err != nil {
		return err
	}
	if err := decoder.Decode(new(interface{})); err != io.EOF {
		return gorm.ErrInvalidData
	}
	return nil
}
func oneOf(value string, allowed ...string) bool {
	for _, candidate := range allowed {
		if value == candidate {
			return true
		}
	}
	return false
}
func validOptional(value *string, allowed ...string) bool {
	return value == nil || oneOf(*value, allowed...)
}

// validateDocumentV1 mirrors the provisional worker contract at the trust boundary.
func validateDocumentV1(data []byte, postType db.PostType, slideCount int) (map[string]struct{}, error) {
	var doc struct {
		SchemaVersion int               `json:"schemaVersion"`
		PostType      string            `json:"postType"`
		Slides        []json.RawMessage `json:"slides"`
	}
	invalid := func() (map[string]struct{}, error) { return nil, gorm.ErrInvalidData }
	if decodeStructured(data, &doc) != nil || doc.SchemaVersion != 1 || doc.PostType != string(postType) || !oneOf(doc.PostType, "single", "carousel") || len(doc.Slides) != slideCount || len(doc.Slides) < 1 || len(doc.Slides) > 20 || (doc.PostType == "single" && len(doc.Slides) != 1) {
		return invalid()
	}
	used := map[string]struct{}{}
	slideIDs := map[string]bool{}
	for _, rawSlide := range doc.Slides {
		var slide struct {
			ID         string `json:"id"`
			Layout     string `json:"layout"`
			Background struct {
				Type  string `json:"type"`
				Color string `json:"color"`
			} `json:"background"`
			Elements []json.RawMessage `json:"elements"`
		}
		if decodeStructured(rawSlide, &slide) != nil || !structuredID.MatchString(slide.ID) || slideIDs[slide.ID] || !oneOf(slide.Layout, "hero", "editorial", "quote") || slide.Background.Type != "solid" || !structuredColor.MatchString(slide.Background.Color) || len(slide.Elements) < 1 || len(slide.Elements) > 12 {
			return invalid()
		}
		slideIDs[slide.ID] = true
		elementIDs := map[string]bool{}
		for _, rawElement := range slide.Elements {
			var kind struct {
				Type string `json:"type"`
			}
			if json.Unmarshal(rawElement, &kind) != nil {
				return invalid()
			}
			var id string
			switch kind.Type {
			case "text":
				var e struct {
					ID      string `json:"id"`
					Type    string `json:"type"`
					Role    string `json:"role"`
					Content string `json:"content"`
					Style   struct {
						Color     string  `json:"color"`
						Size      string  `json:"size"`
						Font      *string `json:"font"`
						Weight    *string `json:"weight"`
						Alignment *string `json:"alignment"`
					} `json:"style"`
				}
				if decodeStructured(rawElement, &e) != nil || !oneOf(e.Role, "heading", "body", "caption", "cta") || !utf8.ValidString(e.Content) || utf8.RuneCountInString(e.Content) > 2000 || strings.TrimSpace(e.Content) == "" || structuredUnsafeText.MatchString(e.Content) || !structuredColor.MatchString(e.Style.Color) || !oneOf(e.Style.Size, "small", "medium", "large") || !validOptional(e.Style.Font, "plus_jakarta_sans", "inter") || !validOptional(e.Style.Weight, "regular", "medium", "bold") || !validOptional(e.Style.Alignment, "left", "center", "right") {
					return invalid()
				}
				var fields map[string]json.RawMessage
				var style map[string]json.RawMessage
				if json.Unmarshal(rawElement, &fields) != nil || json.Unmarshal(fields["style"], &style) != nil {
					return invalid()
				}
				for _, key := range []string{"font", "weight", "alignment"} {
					if value, exists := style[key]; exists && bytes.Equal(bytes.TrimSpace(value), []byte("null")) {
						return invalid()
					}
				}
				id = e.ID
			case "image":
				var e struct {
					ID      string `json:"id"`
					Type    string `json:"type"`
					AssetID string `json:"assetId"`
					Fit     string `json:"fit"`
				}
				if decodeStructured(rawElement, &e) != nil || !structuredID.MatchString(e.AssetID) || !oneOf(e.Fit, "cover", "contain") {
					return invalid()
				}
				id = e.ID
				used[e.AssetID] = struct{}{}
			default:
				return invalid()
			}
			if !structuredID.MatchString(id) || elementIDs[id] {
				return invalid()
			}
			elementIDs[id] = true
		}
	}
	return used, nil
}
