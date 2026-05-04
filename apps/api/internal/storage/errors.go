package storage

import (
	"errors"

	s3types "github.com/aws/aws-sdk-go-v2/service/s3/types"
	"github.com/aws/smithy-go"
)

// ErrObjectNotFound is a test-friendly sentinel; production paths use AWS SDK errors classified below.
var ErrObjectNotFound = errors.New("storage: object not found")

// IsObjectNotFound reports whether err indicates the S3 object does not exist (or the test sentinel).
func IsObjectNotFound(err error) bool {
	if err == nil {
		return false
	}
	if errors.Is(err, ErrObjectNotFound) {
		return true
	}
	var nk *s3types.NoSuchKey
	if errors.As(err, &nk) {
		return true
	}
	var nf *s3types.NotFound
	if errors.As(err, &nf) {
		return true
	}
	var apiErr smithy.APIError
	if errors.As(err, &apiErr) {
		switch apiErr.ErrorCode() {
		case "NoSuchKey", "NotFound":
			return true
		}
	}
	return false
}
