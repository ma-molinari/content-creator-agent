//go:build integration

package integration

import (
	"context"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"testing"
	"time"

	"content-creator-agent/internal/storage"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

// Opt in only against a loopback LocalStack instance with the postmind-local bucket.
func TestLocalStackS3RoundTrip(t *testing.T) {
	endpoint := os.Getenv("LOCALSTACK_TEST_ENDPOINT")
	if endpoint == "" {
		t.Skip("LOCALSTACK_TEST_ENDPOINT not configured")
	}
	parsed, err := url.Parse(endpoint)
	require.NoError(t, err)
	ip := net.ParseIP(parsed.Hostname())
	require.True(t, parsed.Hostname() == "localhost" || (ip != nil && ip.IsLoopback()), "test endpoint must be loopback")
	t.Setenv("AWS_ENDPOINT_URL", endpoint)
	t.Setenv("AWS_ENDPOINT_URL_S3", endpoint)
	service, err := storage.NewS3Service("us-east-1", "postmind-local", "test", "test", storage.S3Options{ForcePathStyle: true, PublicEndpoint: endpoint})
	require.NoError(t, err)
	ctx := context.Background()
	key := "integration-test/" + uuid.NewString()
	t.Cleanup(func() { _ = service.Delete(context.Background(), key) })
	require.NoError(t, service.Upload(ctx, key, []byte("local-test")))
	require.NoError(t, service.HeadObject(ctx, key))
	data, err := service.GetObject(ctx, key)
	require.NoError(t, err)
	require.Equal(t, []byte("local-test"), data)
	signed, err := service.GetSignedURL(ctx, key, time.Minute)
	require.NoError(t, err)
	client := &http.Client{Timeout: 5 * time.Second}
	response, err := client.Get(signed)
	require.NoError(t, err)
	defer response.Body.Close()
	require.Equal(t, http.StatusOK, response.StatusCode)
	data, err = io.ReadAll(response.Body)
	require.NoError(t, err)
	require.Equal(t, []byte("local-test"), data)
	require.NoError(t, service.Delete(ctx, key))
	require.True(t, storage.IsObjectNotFound(service.HeadObject(ctx, key)))
}
