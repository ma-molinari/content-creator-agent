package jobs

import (
	"context"
	"fmt"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

func TestV2CapabilityPoolFailsClosedAndDispatchesDedicatedRoute(t *testing.T) {
	var old atomic.Bool
	var changed atomic.Bool
	var route atomic.Value
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/capabilities" {
			if old.Load() {
				fmt.Fprint(w, `{"structuredPost":{"contractVersion":1}}`)
				return
			}
			fmt.Fprint(w, `{"structuredPost":{"contractVersion":1,"readSchemas":[1,2],"writeSchemas":[1,2],"decorationOperations":true}}`)
			return
		}
		route.Store(r.URL.Path)
		if changed.Load() {
			http.NotFound(w, r)
			return
		}
		w.WriteHeader(http.StatusAccepted)
	}))
	defer server.Close()
	pool, err := NewStructuredWorkerPool(&legacyCapture{}, []string{server.URL}, "key")
	require.NoError(t, err)
	require.True(t, pool.SupportsStructured(context.Background()))
	for _, read := range []int{0, 1, 2} {
		require.True(t, pool.SupportsStructuredV2(context.Background(), read))
	}
	require.False(t, pool.SupportsStructuredV2(context.Background(), 3))
	target := 2
	payload := DispatchPayload{JobID: uuid.New(), PostFormat: "structured_v1", TargetSchemaVersion: &target}
	require.NoError(t, pool.DispatchJob(context.Background(), payload))
	require.Equal(t, "/jobs/structured/v2", route.Load())
	old.Store(true)
	require.True(t, pool.SupportsStructured(context.Background()))
	require.False(t, pool.SupportsStructuredV2(context.Background(), 1))
	old.Store(false)
	changed.Store(true)
	require.Error(t, pool.DispatchJob(context.Background(), payload))
	require.Equal(t, "/jobs/structured/v2", route.Load())
}

func TestV2RequiresEveryDestinationAndExactReadCapability(t *testing.T) {
	makeServer := func(read string) *httptest.Server {
		return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			fmt.Fprintf(w, `{"structuredPost":{"contractVersion":1,"readSchemas":%s,"writeSchemas":[2],"decorationOperations":true}}`, read)
		}))
	}
	first, second := makeServer(`[1,2]`), makeServer(`[1]`)
	defer first.Close()
	defer second.Close()
	pool, err := NewStructuredWorkerPool(&legacyCapture{}, []string{first.URL, second.URL}, "key")
	require.NoError(t, err)
	require.True(t, pool.SupportsStructuredV2(context.Background(), 0))
	require.True(t, pool.SupportsStructuredV2(context.Background(), 1))
	require.False(t, pool.SupportsStructuredV2(context.Background(), 2))
}

func TestV2ProbeRejectsRedirectAndBadResponses(t *testing.T) {
	for _, handler := range []http.HandlerFunc{
		func(w http.ResponseWriter, r *http.Request) {
			http.Redirect(w, r, "https://example.invalid", http.StatusFound)
		},
		func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(http.StatusServiceUnavailable) },
		func(w http.ResponseWriter, r *http.Request) {
			fmt.Fprint(w, `{"structuredPost":{"contractVersion":1,"readSchemas":[1,2],"writeSchemas":[2]}}`)
		},
	} {
		server := httptest.NewServer(handler)
		pool, err := NewStructuredWorkerPool(&legacyCapture{}, []string{server.URL}, "key")
		require.NoError(t, err)
		require.False(t, pool.SupportsStructuredV2(context.Background(), 1))
		server.Close()
	}
}

func TestV3RequiresAllWorkersAndDedicatedRoute(t *testing.T) {
	var ready atomic.Bool
	var route atomic.Value
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/capabilities" {
			if ready.Load() {
				fmt.Fprint(w, `{"structuredPost":{"contractVersion":1,"readSchemas":[1,2,3],"writeSchemas":[1,2,3],"decorationOperations":true,"stockImageOperations":true,"imageCompositionVersion":2}}`)
			} else {
				fmt.Fprint(w, `{"structuredPost":{"contractVersion":1,"readSchemas":[1,2],"writeSchemas":[1,2],"decorationOperations":true}}`)
			}
			return
		}
		route.Store(r.URL.Path)
		w.WriteHeader(http.StatusAccepted)
	}))
	defer server.Close()
	pool, err := NewStructuredWorkerPool(&legacyCapture{}, []string{server.URL}, "key")
	require.NoError(t, err)
	require.False(t, pool.SupportsStructuredV3(context.Background(), 0))
	ready.Store(true)
	for _, read := range []int{0, 1, 2, 3} {
		require.True(t, pool.SupportsStructuredV3(context.Background(), read))
	}
	version := 3
	require.NoError(t, pool.DispatchJob(context.Background(), DispatchPayload{JobID: uuid.New(), PostFormat: "structured_v1", TargetSchemaVersion: &version}))
	require.Equal(t, "/jobs/structured/v3", route.Load())
}

func TestV3RejectsWorkerWithoutFocalCompositionCapability(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprint(w, `{"structuredPost":{"contractVersion":1,"readSchemas":[1,2,3],"writeSchemas":[1,2,3],"decorationOperations":true,"stockImageOperations":true}}`)
	}))
	defer server.Close()
	pool, err := NewStructuredWorkerPool(&legacyCapture{}, []string{server.URL}, "key")
	require.NoError(t, err)
	require.False(t, pool.SupportsStructuredV3(context.Background(), 3))
}

func TestReferencePolicyRequiresEveryWorker(t *testing.T) {
	var old atomic.Bool
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if old.Load() {
			fmt.Fprint(w, `{"structuredPost":{"contractVersion":1}}`)
		} else {
			fmt.Fprint(w, `{"structuredPost":{"contractVersion":1,"referencePolicyVersion":1}}`)
		}
	}))
	defer server.Close()
	pool, err := NewStructuredWorkerPool(&legacyCapture{}, []string{server.URL}, "key")
	require.NoError(t, err)
	require.True(t, pool.SupportsReferencePolicy(context.Background()))
	old.Store(true)
	require.True(t, pool.SupportsStructured(context.Background()))
	require.False(t, pool.SupportsReferencePolicy(context.Background()))
}
