package storage

import (
	"context"
	"time"
)

// Nop is a no-op storage before S3 (T9–T11); replaced in T13.
type Nop struct{}

func (Nop) Upload(ctx context.Context, key string, data []byte) error { return nil }

func (Nop) GetSignedURL(ctx context.Context, key string, expiry time.Duration) (string, error) {
	return "https://example.com/signed", nil
}

func (Nop) GetObject(ctx context.Context, key string) ([]byte, error) { return []byte{0xff, 0xd8}, nil }

func (Nop) Delete(ctx context.Context, key string) error { return nil }

func (Nop) DeleteMany(ctx context.Context, keys []string) error { return nil }
