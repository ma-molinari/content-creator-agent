package jobs

import (
	"errors"
	"strings"

	"github.com/google/uuid"
)

// ErrInvalidSlideS3Key means the worker supplied an object key outside slides/{jobID}/.
var ErrInvalidSlideS3Key = errors.New("invalid slide s3 key")

func validateSlideArtifactKey(jobID uuid.UUID, key string) error {
	if strings.Contains(key, "..") || strings.Contains(key, "\\") {
		return ErrInvalidSlideS3Key
	}
	if strings.HasPrefix(key, "/") {
		return ErrInvalidSlideS3Key
	}
	want := "slides/" + jobID.String() + "/"
	if !strings.HasPrefix(key, want) {
		return ErrInvalidSlideS3Key
	}
	if key[len(want):] == "" {
		return ErrInvalidSlideS3Key
	}
	return nil
}
