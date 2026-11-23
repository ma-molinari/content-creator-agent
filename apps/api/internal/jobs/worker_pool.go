package jobs

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"strings"
	"sync/atomic"
)

// StructuredWorkerPool probes and dispatches to the same explicitly configured destinations.
// Each URL must resolve to one worker; a load-balanced URL cannot guarantee replica compatibility.
type StructuredWorkerPool struct {
	legacy     WorkerClient
	structured []*HTTPWorkerClient
	next       uint64
}

// SupportsStructuredV2 probes every direct destination used by DispatchJob.
func (p *StructuredWorkerPool) SupportsStructuredV2(ctx context.Context, readSchema int) bool {
	if len(p.structured) == 0 {
		log.Printf("[metrics] event=worker_capability schema_version=2 outcome=unavailable")
		return false
	}
	for _, worker := range p.structured {
		if !worker.SupportsStructuredV2(ctx, readSchema) {
			log.Printf("[metrics] event=worker_capability schema_version=2 outcome=unavailable")
			return false
		}
	}
	return true
}

func NewStructuredWorkerPool(legacy WorkerClient, addresses []string, apiKey string) (*StructuredWorkerPool, error) {
	pool := &StructuredWorkerPool{legacy: legacy}
	seen := map[string]bool{}
	for _, raw := range addresses {
		address := strings.TrimRight(strings.TrimSpace(raw), "/")
		u, err := url.Parse(address)
		if err != nil || (u.Scheme != "http" && u.Scheme != "https") || u.Host == "" || u.User != nil || u.RawQuery != "" || u.Fragment != "" || seen[address] {
			return nil, fmt.Errorf("invalid structured worker address")
		}
		seen[address] = true
		client := NewHTTPWorkerClient(address, apiKey)
		client.httpClient.CheckRedirect = func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }
		pool.structured = append(pool.structured, client)
	}
	return pool, nil
}

func (p *StructuredWorkerPool) SupportsStructured(ctx context.Context) bool {
	if len(p.structured) == 0 {
		return false
	}
	for _, worker := range p.structured {
		if !worker.SupportsStructured(ctx) {
			return false
		}
	}
	return true
}

// SupportsReferencePolicy requires every eligible worker to enforce reference separation.
func (p *StructuredWorkerPool) SupportsReferencePolicy(ctx context.Context) bool {
	if len(p.structured) == 0 {
		return false
	}
	for _, worker := range p.structured {
		if !worker.SupportsReferencePolicy(ctx) {
			return false
		}
	}
	return true
}

func (p *StructuredWorkerPool) DispatchJob(ctx context.Context, payload DispatchPayload) error {
	if payload.PostFormat != "structured_v1" {
		return p.legacy.DispatchJob(ctx, payload)
	}
	if len(p.structured) == 0 {
		return fmt.Errorf("no structured worker destinations")
	}
	index := (atomic.AddUint64(&p.next, 1) - 1) % uint64(len(p.structured))
	return p.structured[index].DispatchJob(ctx, payload)
}
