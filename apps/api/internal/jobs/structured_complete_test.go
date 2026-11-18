package jobs

import (
	"context"
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
	valid := []byte(`{"schemaVersion":1,"postType":"single","slides":[{}]}`)
	cases := []struct {
		name        string
		data        []byte
		contentType string
		count       int
		valid       bool
	}{
		{"valid", valid, "application/json; charset=utf-8", 1, true},
		{"wrong content type", valid, "text/html", 1, false},
		{"malformed", []byte(`{`), "application/json", 1, false},
		{"wrong schema", []byte(`{"schemaVersion":2,"postType":"single","slides":[{}]}`), "application/json", 1, false},
		{"wrong type", []byte(`{"schemaVersion":1,"postType":"carousel","slides":[{}]}`), "application/json", 1, false},
		{"wrong count", valid, "application/json", 2, false},
		{"null slide", []byte(`{"schemaVersion":1,"postType":"single","slides":[null]}`), "application/json", 1, false},
		{"too large", make([]byte, maxStructuredDocumentBytes+1), "application/json", 1, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			err := validateStructuredDocument(context.Background(), documentStore{data: tc.data, contentType: tc.contentType}, "test", db.PostTypeSingle, tc.count)
			if tc.valid {
				require.NoError(t, err)
			} else {
				require.Error(t, err)
			}
		})
	}
	require.Error(t, validateStructuredDocument(context.Background(), testStore{}, "test", db.PostTypeSingle, 1))
}
