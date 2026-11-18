package chat

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"mime"
	"regexp"
	"strings"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/storage"
)

const maxAssetManifestBytes int64 = 64 * 1024

var assetIDPattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`)

type boundedAssetStore interface {
	GetObjectLimited(context.Context, string, int64) ([]byte, string, error)
}

// inheritedAssetSources validates a manifest belonging to an already authorized base version.
func inheritedAssetSources(ctx context.Context, store storage.StorageService, base db.PostVersion) (map[string]string, error) {
	bounded, ok := store.(boundedAssetStore)
	if !ok {
		return nil, errors.New("bounded asset storage unavailable")
	}
	prefix := fmt.Sprintf("slides/%s/", base.JobID)
	raw, contentType, err := bounded.GetObjectLimited(ctx, prefix+"assets.json", maxAssetManifestBytes)
	if err != nil {
		return nil, err
	}
	mediaType, _, err := mime.ParseMediaType(contentType)
	if err != nil || mediaType != "application/json" || int64(len(raw)) > maxAssetManifestBytes {
		return nil, errors.New("invalid asset manifest")
	}
	var sources map[string]string
	if json.Unmarshal(raw, &sources) != nil || sources == nil || len(sources) > 240 {
		return nil, errors.New("invalid asset manifest")
	}
	for id, key := range sources {
		if !assetIDPattern.MatchString(id) {
			return nil, errors.New("invalid asset manifest")
		}
		expected := prefix + "assets/" + id + "."
		ext := strings.TrimPrefix(key, expected)
		if !strings.HasPrefix(key, expected) || (ext != "jpg" && ext != "png" && ext != "webp") {
			return nil, errors.New("invalid asset manifest")
		}
	}
	return sources, nil
}
