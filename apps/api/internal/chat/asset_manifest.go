package chat

import (
	"context"
	"errors"
	"fmt"
	"mime"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/storage"
)

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
	raw, contentType, err := bounded.GetObjectLimited(ctx, prefix+"assets.json", storage.MaxAssetManifestBytes)
	if err != nil {
		return nil, err
	}
	mediaType, _, err := mime.ParseMediaType(contentType)
	if err != nil || mediaType != "application/json" || int64(len(raw)) > storage.MaxAssetManifestBytes {
		return nil, errors.New("invalid asset manifest")
	}
	return storage.ValidateAssetManifest(raw, base.JobID)
}
