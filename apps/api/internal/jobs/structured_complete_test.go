package jobs

import (
	"context"
	"strings"
	"testing"

	"content-creator-agent/internal/db"
	"github.com/stretchr/testify/require"
)

type documentStore struct {
	testStore
	data        []byte
	contentType string
}

func (s documentStore) GetObjectLimited(_ context.Context, _ string, _ int64) ([]byte, string, error) {
	return s.data, s.contentType, nil
}

func TestValidateStructuredDocument(t *testing.T) {
	valid := []byte(`{"schemaVersion":1,"postType":"single","slides":[{"id":"s1","layout":"hero","background":{"type":"solid","color":"#000000"},"elements":[{"id":"t1","type":"text","role":"heading","content":"Olá","style":{"color":"#ffffff","size":"large"}}]}]}`)
	cases := []struct {
		name        string
		data        []byte
		contentType string
		count       int
		valid       bool
	}{
		{"valid", valid, "application/json; charset=utf-8", 1, true},
		{"wrong content type", valid, "text/html", 1, false},
		{"unknown field", []byte(strings.Replace(string(valid), `"layout":"hero"`, `"layout":"hero","extra":true`, 1)), "application/json", 1, false},
		{"unsafe text", []byte(strings.Replace(string(valid), "Olá", "https://example.com", 1)), "application/json", 1, false},
		{"duplicate element IDs", []byte(strings.Replace(string(valid), `"elements":[`, `"elements":[{"id":"t1","type":"image","assetId":"a1","fit":"cover"},`, 1)), "application/json", 1, false},
		{"invalid layout", []byte(strings.Replace(string(valid), `"hero"`, `"unknown"`, 1)), "application/json", 1, false},
		{"null optional style", []byte(strings.Replace(string(valid), `"size":"large"`, `"size":"large","font":null`, 1)), "application/json", 1, false},
		{"malformed", []byte(`{`), "application/json", 1, false},
		{"wrong schema", []byte(`{"schemaVersion":2,"postType":"single","slides":[{}]}`), "application/json", 1, false},
		{"wrong type", []byte(`{"schemaVersion":1,"postType":"carousel","slides":[{}]}`), "application/json", 1, false},
		{"wrong count", valid, "application/json", 2, false},
		{"null slide", []byte(`{"schemaVersion":1,"postType":"single","slides":[null]}`), "application/json", 1, false},
		{"too large", make([]byte, maxStructuredDocumentBytes+1), "application/json", 1, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := validateStructuredDocument(context.Background(), documentStore{data: tc.data, contentType: tc.contentType}, "test", db.PostTypeSingle, tc.count)
			if tc.valid {
				require.NoError(t, err)
			} else {
				require.Error(t, err)
			}
		})
	}
	_, err := validateStructuredDocument(context.Background(), testStore{}, "test", db.PostTypeSingle, 1)
	require.Error(t, err)
}
