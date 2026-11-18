package jobs

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

func TestStructuredCapabilityAndDedicatedDispatch(t *testing.T) {
	var dispatchedPath string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		require.Equal(t, "test-key", r.Header.Get("X-Worker-API-Key"))
		if r.URL.Path == "/capabilities" {
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write([]byte(`{"structuredPost":{"contractVersion":1}}`))
			return
		}
		dispatchedPath = r.URL.Path
		w.WriteHeader(http.StatusAccepted)
	}))
	defer server.Close()
	client := NewHTTPWorkerClient(server.URL, "test-key")
	require.True(t, client.SupportsStructured(context.Background()))
	require.NoError(t, client.DispatchJob(context.Background(), DispatchPayload{JobID: uuid.New(), PostFormat: "structured_v1"}))
	require.Equal(t, "/jobs/structured", dispatchedPath)
	require.NoError(t, client.DispatchJob(context.Background(), DispatchPayload{JobID: uuid.New(), PostFormat: "legacy_html"}))
	require.Equal(t, "/jobs", dispatchedPath)
}

func TestOldWorkerDoesNotAdvertiseStructuredCapability(t *testing.T) {
	server := httptest.NewServer(http.NotFoundHandler())
	defer server.Close()
	require.False(t, NewHTTPWorkerClient(server.URL, "test-key").SupportsStructured(context.Background()))
}
