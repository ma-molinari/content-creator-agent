package jobs

import (
	"encoding/json"

	"content-creator-agent/internal/db"
	"gorm.io/gorm"
)

func validColorRef(raw json.RawMessage) bool {
	var color map[string]json.RawMessage
	if json.Unmarshal(raw, &color) != nil || len(color) != 1 {
		return false
	}
	var value string
	if token, ok := color["token"]; ok {
		return json.Unmarshal(token, &value) == nil && oneOf(value, "background", "text", "accent")
	}
	if hex, ok := color["hex"]; ok {
		return json.Unmarshal(hex, &value) == nil && structuredColor.MatchString(value)
	}
	return false
}

// validateDocumentV2 validates V2 without enabling publication on the V1 callback.
func validateDocumentV2(data []byte, postType db.PostType, slideCount int) (map[string]struct{}, error) {
	invalid := func() (map[string]struct{}, error) { return nil, gorm.ErrInvalidData }
	var doc struct {
		SchemaVersion int    `json:"schemaVersion"`
		PostType      string `json:"postType"`
		Palette       struct {
			Background string `json:"background"`
			Text       string `json:"text"`
			Accent     string `json:"accent"`
		} `json:"palette"`
		Slides []json.RawMessage `json:"slides"`
	}
	if decodeStructured(data, &doc) != nil || doc.SchemaVersion != 2 || !structuredColor.MatchString(doc.Palette.Background) || !structuredColor.MatchString(doc.Palette.Text) || !structuredColor.MatchString(doc.Palette.Accent) {
		return invalid()
	}
	converted := make([]json.RawMessage, 0, len(doc.Slides))
	for _, raw := range doc.Slides {
		var slide struct {
			ID         string `json:"id"`
			Layout     string `json:"layout"`
			Background struct {
				Type  string          `json:"type"`
				Color json.RawMessage `json:"color"`
			} `json:"background"`
			Elements []json.RawMessage `json:"elements"`
		}
		if decodeStructured(raw, &slide) != nil || slide.Background.Type != "solid" || !validColorRef(slide.Background.Color) || len(slide.Elements) < 1 || len(slide.Elements) > 12 {
			return invalid()
		}
		ids := map[string]bool{}
		var elements []json.RawMessage
		decorations := 0
		for _, rawElement := range slide.Elements {
			var kind struct {
				ID   string `json:"id"`
				Type string `json:"type"`
			}
			if json.Unmarshal(rawElement, &kind) != nil || !structuredID.MatchString(kind.ID) || ids[kind.ID] {
				return invalid()
			}
			ids[kind.ID] = true
			switch kind.Type {
			case "decoration":
				var e struct {
					ID        string          `json:"id"`
					Type      string          `json:"type"`
					Kind      string          `json:"kind"`
					Color     json.RawMessage `json:"color"`
					Width     string          `json:"width"`
					Thickness string          `json:"thickness"`
					Corner    string          `json:"corner"`
				}
				if decodeStructured(rawElement, &e) != nil || !oneOf(e.Kind, "bar", "line") || !validColorRef(e.Color) || !oneOf(e.Width, "short", "medium", "full") || !oneOf(e.Thickness, "thin", "medium", "thick") || !oneOf(e.Corner, "square", "rounded") || (e.Kind == "line" && e.Corner != "square") {
					return invalid()
				}
				decorations++
				if decorations > 4 {
					return invalid()
				}
			case "text":
				var fields map[string]json.RawMessage
				var style map[string]json.RawMessage
				if json.Unmarshal(rawElement, &fields) != nil || json.Unmarshal(fields["style"], &style) != nil || !validColorRef(style["color"]) {
					return invalid()
				}
				style["color"] = json.RawMessage(`"#000000"`)
				fields["style"], _ = json.Marshal(style)
				element, _ := json.Marshal(fields)
				elements = append(elements, element)
			case "image":
				elements = append(elements, rawElement)
			default:
				return invalid()
			}
		}
		if len(elements) == 0 {
			elements = append(elements, json.RawMessage(`{"id":"placeholder","type":"text","role":"body","content":"x","style":{"color":"#000000","size":"small"}}`))
		}
		v1Slide, err := json.Marshal(map[string]interface{}{"id": slide.ID, "layout": slide.Layout, "background": map[string]string{"type": "solid", "color": "#000000"}, "elements": elements})
		if err != nil {
			return invalid()
		}
		converted = append(converted, v1Slide)
	}
	v1, err := json.Marshal(map[string]interface{}{"schemaVersion": 1, "postType": doc.PostType, "slides": converted})
	if err != nil {
		return invalid()
	}
	return validateDocumentV1(v1, postType, slideCount)
}
