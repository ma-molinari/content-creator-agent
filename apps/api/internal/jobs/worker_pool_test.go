package jobs

import (
	"context"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"

	"github.com/stretchr/testify/require"
)

type legacyCapture struct{ calls int }

func (l *legacyCapture) DispatchJob(context.Context, DispatchPayload) error { l.calls++; return nil }

func TestStructuredWorkerPoolChecksEveryDestinationAndRoutesDirectly(t *testing.T) {
	var compatible atomic.Bool
	compatible.Store(true)
	var received [2]atomic.Int32
	server := func(i int) *httptest.Server {
		return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			require.Equal(t, "key", r.Header.Get("X-Worker-API-Key"))
			if r.URL.Path == "/capabilities" {
				if i == 1 && !compatible.Load() {
					http.NotFound(w, r)
					return
				}
				_, _ = w.Write([]byte(`{"structuredPost":{"contractVersion":1}}`))
				return
			}
			require.Equal(t, "/jobs/structured", r.URL.Path)
			received[i].Add(1)
			w.WriteHeader(http.StatusAccepted)
		}))
	}
	first, second := server(0), server(1)
	defer first.Close()
	defer second.Close()
	legacy := &legacyCapture{}
	pool, err := NewStructuredWorkerPool(legacy, []string{first.URL, second.URL}, "key")
	require.NoError(t, err)
	require.True(t, pool.SupportsStructured(context.Background()))
	require.NoError(t, pool.DispatchJob(context.Background(), DispatchPayload{PostFormat: "structured_v1"}))
	require.NoError(t, pool.DispatchJob(context.Background(), DispatchPayload{PostFormat: "structured_v1"}))
	require.EqualValues(t, 1, received[0].Load())
	require.EqualValues(t, 1, received[1].Load())
	require.NoError(t, pool.DispatchJob(context.Background(), DispatchPayload{PostFormat: "legacy_html"}))
	require.Equal(t, 1, legacy.calls)
	compatible.Store(false)
	require.False(t, pool.SupportsStructured(context.Background()))
}

func TestStructuredWorkerPoolFailsClosedForEmptyOrInvalidConfiguration(t *testing.T) {
	pool, err := NewStructuredWorkerPool(&legacyCapture{}, nil, "key")
	require.NoError(t, err)
	require.False(t, pool.SupportsStructured(context.Background()))
	require.Error(t, pool.DispatchJob(context.Background(), DispatchPayload{PostFormat: "structured_v1"}))
	for _, addresses := range [][]string{{"ftp://worker"}, {"http://user:secret@worker"}, {"http://worker?query=yes"}, {"http://worker", "http://worker/"}} {
		_, err := NewStructuredWorkerPool(&legacyCapture{}, addresses, "key")
		require.Error(t, err)
	}
}

func TestStructuredWorkerPoolDoesNotFollowRedirects(t *testing.T) {
	target := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(`{"structuredPost":{"contractVersion":1}}`))
	}))
	defer target.Close()
	redirect := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { http.Redirect(w, r, target.URL, http.StatusFound) }))
	defer redirect.Close()
	pool, err := NewStructuredWorkerPool(&legacyCapture{}, []string{redirect.URL}, "key")
	require.NoError(t, err)
	require.False(t, pool.SupportsStructured(context.Background()))
}
