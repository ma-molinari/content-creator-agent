package storage

import (
	"encoding/json"
	"errors"
	"fmt"
	"regexp"
	"strings"

	"github.com/google/uuid"
)

const MaxAssetManifestBytes int64 = 64 * 1024

var assetIDPattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`)

// ValidateAssetManifest permits only stable asset keys under the owning job's prefix.
func ValidateAssetManifest(raw []byte, jobID uuid.UUID) (map[string]string, error) {
	var sources map[string]string
	if int64(len(raw)) > MaxAssetManifestBytes || json.Unmarshal(raw, &sources) != nil || sources == nil || len(sources) > 240 {
		return nil, errors.New("invalid asset manifest")
	}
	prefix := fmt.Sprintf("slides/%s/assets/", jobID)
	for id, key := range sources {
		if !assetIDPattern.MatchString(id) {
			return nil, errors.New("invalid asset manifest")
		}
		expected := prefix + id + "."
		ext := strings.TrimPrefix(key, expected)
		if !strings.HasPrefix(key, expected) || (ext != "jpg" && ext != "png" && ext != "webp") {
			return nil, errors.New("invalid asset manifest")
		}
	}
	return sources, nil
}
