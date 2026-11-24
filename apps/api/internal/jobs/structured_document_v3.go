package jobs

import (
	"bytes"
	"encoding/json"
	"net/url"
	"unicode/utf8"

	"content-creator-agent/internal/db"
	"gorm.io/gorm"
)

func validCreditURL(value string) bool {
	u, err := url.Parse(value)
	return err == nil && len(value) > 0 && len(value) <= 2048 && u.Scheme == "https" && u.Hostname() != "" && u.User == nil && (u.Port() == "" || u.Port() == "443")
}

// validateDocumentV3 validates image backgrounds and provenance before publication.
func validateDocumentV3(data []byte, postType db.PostType, slideCount int) (map[string]struct{}, error) {
	invalid := func() (map[string]struct{}, error) { return nil, gorm.ErrInvalidData }
	var doc struct {
		SchemaVersion int               `json:"schemaVersion"`
		PostType      string            `json:"postType"`
		Palette       json.RawMessage   `json:"palette"`
		Slides        []json.RawMessage `json:"slides"`
		Credits       map[string]struct {
			Title      *string `json:"title"`
			Creator    *string `json:"creator"`
			SourceURL  string  `json:"sourceUrl"`
			License    string  `json:"license"`
			LicenseURL string  `json:"licenseUrl"`
		} `json:"credits"`
	}
	if decodeStructured(data, &doc) != nil || doc.SchemaVersion != 3 || len(doc.Credits) > 240 {
		return invalid()
	}
	var fields map[string]json.RawMessage
	if json.Unmarshal(data, &fields) != nil || bytes.Equal(bytes.TrimSpace(fields["credits"]), []byte("null")) {
		return invalid()
	}
	backgroundAssets := make(map[string]struct{})
	converted := make([]json.RawMessage, 0, len(doc.Slides))
	for _, raw := range doc.Slides {
		var slide map[string]json.RawMessage
		var background map[string]json.RawMessage
		if json.Unmarshal(raw, &slide) != nil || json.Unmarshal(slide["background"], &background) != nil {
			return invalid()
		}
		var kind string
		if json.Unmarshal(background["type"], &kind) != nil {
			return invalid()
		}
		if kind == "image" {
			var assetID string
			if len(background) != 2 || json.Unmarshal(background["assetId"], &assetID) != nil || !structuredID.MatchString(assetID) {
				return invalid()
			}
			backgroundAssets[assetID] = struct{}{}
			slide["background"] = json.RawMessage(`{"type":"solid","color":{"token":"background"}}`)
		}
		convertedSlide, err := json.Marshal(slide)
		if err != nil {
			return invalid()
		}
		converted = append(converted, convertedSlide)
	}
	v2, err := json.Marshal(map[string]interface{}{"schemaVersion": 2, "postType": doc.PostType, "palette": doc.Palette, "slides": converted})
	if err != nil {
		return invalid()
	}
	used, err := validateDocumentV2(v2, postType, slideCount)
	if err != nil {
		return invalid()
	}
	for id := range backgroundAssets {
		used[id] = struct{}{}
	}
	for id, credit := range doc.Credits {
		_, ok := used[id]
		if !ok || !structuredID.MatchString(id) || credit.Title == nil || !utf8.ValidString(*credit.Title) || utf8.RuneCountInString(*credit.Title) > 500 ||
			(credit.Creator != nil && (!utf8.ValidString(*credit.Creator) || utf8.RuneCountInString(*credit.Creator) > 500)) ||
			credit.License != "cc0" || !validCreditURL(credit.SourceURL) || !validCreditURL(credit.LicenseURL) {
			return invalid()
		}
	}
	return used, nil
}
