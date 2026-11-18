package chat

import (
	"context"
	"fmt"
	"testing"

	"content-creator-agent/internal/db"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

type manifestStore struct {
	mockStorage
	data        []byte
	contentType string
}

func (s *manifestStore) GetObjectLimited(_ context.Context, _ string, _ int64) ([]byte, string, error) {
	return s.data, s.contentType, nil
}

func TestInheritedAssetSources(t *testing.T) {
	jobID := uuid.New()
	prefix := fmt.Sprintf("slides/%s/assets/", jobID)
	version := db.PostVersion{JobID: jobID}
	cases := []struct {
		name        string
		payload     string
		contentType string
		valid       bool
	}{
		{"valid", fmt.Sprintf(`{"asset-1":%q}`, prefix+"asset-1.png"), "application/json", true},
		{"empty", `{}`, "application/json", true},
		{"foreign job", `{"asset-1":"slides/other/assets/asset-1.png"}`, "application/json", false},
		{"wrong id", fmt.Sprintf(`{"asset-1":%q}`, prefix+"asset-2.png"), "application/json", false},
		{"traversal", fmt.Sprintf(`{"..":%q}`, prefix+"...png"), "application/json", false},
		{"wrong type", `{}`, "text/html", false},
		{"null", `null`, "application/json", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			out, err := inheritedAssetSources(context.Background(), &manifestStore{data: []byte(tc.payload), contentType: tc.contentType}, version)
			if tc.valid {
				require.NoError(t, err)
				require.NotNil(t, out)
			} else {
				require.Error(t, err)
			}
		})
	}
}
