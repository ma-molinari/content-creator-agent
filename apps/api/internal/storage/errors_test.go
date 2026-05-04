package storage

import (
	"errors"
	"fmt"
	"testing"

	s3types "github.com/aws/aws-sdk-go-v2/service/s3/types"
	"github.com/stretchr/testify/require"
)

func TestIsObjectNotFound_sentinel(t *testing.T) {
	require.True(t, IsObjectNotFound(ErrObjectNotFound))
	require.True(t, IsObjectNotFound(fmt.Errorf("wrap: %w", ErrObjectNotFound)))
	require.False(t, IsObjectNotFound(nil))
	require.False(t, IsObjectNotFound(errors.New("other")))
}

func TestIsObjectNotFound_awsTypes(t *testing.T) {
	require.True(t, IsObjectNotFound(&s3types.NoSuchKey{}))
	require.True(t, IsObjectNotFound(&s3types.NotFound{}))
	require.True(t, IsObjectNotFound(fmt.Errorf("head: %w", &s3types.NoSuchKey{})))
}
