package storage

import (
	"context"
	"net/http"
	"net/http/httptest"
	"net/url"
	"time"

	"github.com/stretchr/testify/require"
	"testing"
)

func TestDeleteManyEmpty(t *testing.T) {
	s := &S3Service{bucket: "b"}
	if err := s.DeleteMany(context.Background(), nil); err != nil {
		t.Fatal(err)
	}
	if err := s.DeleteMany(context.Background(), []string{}); err != nil {
		t.Fatal(err)
	}
}

func TestPathStyleAndPublicPresignEndpoint(t *testing.T) {
	var requestPath string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { requestPath = r.URL.Path; w.WriteHeader(http.StatusOK) }))
	defer server.Close()
	t.Setenv("AWS_ENDPOINT_URL", server.URL)
	t.Setenv("AWS_ENDPOINT_URL_S3", server.URL)
	service, err := NewS3Service("us-east-1", "postmind-local", "test", "test", S3Options{ForcePathStyle: true, PublicEndpoint: "http://localhost:4566"})
	require.NoError(t, err)
	require.NoError(t, service.Upload(context.Background(), "folder/example", []byte("test")))
	require.Equal(t, "/postmind-local/folder/example", requestPath)
	signed, err := service.GetSignedURL(context.Background(), "folder/example", time.Hour)
	require.NoError(t, err)
	parsed, err := url.Parse(signed)
	require.NoError(t, err)
	require.Equal(t, "localhost:4566", parsed.Host)
	require.Equal(t, "/postmind-local/folder/example", parsed.Path)
	require.NotEmpty(t, parsed.Query().Get("X-Amz-Signature"))
}

func TestRejectsInvalidPublicEndpoint(t *testing.T) {
	for _, endpoint := range []string{"ftp://example.com", "http://user:pass@example.com", "http://example.com?x=1", "http://example.com/#fragment"} {
		_, err := NewS3Service("us-east-1", "bucket", "test", "test", S3Options{PublicEndpoint: endpoint})
		require.Error(t, err)
	}
}
