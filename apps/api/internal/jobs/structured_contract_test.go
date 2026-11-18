package jobs

import (
	"encoding/json"
	"os"
	"testing"

	"content-creator-agent/internal/db"
	"github.com/stretchr/testify/require"
)

func TestSharedStructuredDocumentContract(t *testing.T) {
	data, err := os.ReadFile("../../../../tests/fixtures/structured_documents.json")
	require.NoError(t, err)
	var cases []struct {
		Name     string          `json:"name"`
		Valid    bool            `json:"valid"`
		Document json.RawMessage `json:"document"`
	}
	require.NoError(t, json.Unmarshal(data, &cases))
	for _, tc := range cases {
		t.Run(tc.Name, func(t *testing.T) {
			var doc struct {
				PostType string            `json:"postType"`
				Slides   []json.RawMessage `json:"slides"`
			}
			require.NoError(t, json.Unmarshal(tc.Document, &doc))
			_, err := validateDocumentV1(tc.Document, db.PostType(doc.PostType), len(doc.Slides))
			if tc.Valid {
				require.NoError(t, err)
			} else {
				require.Error(t, err)
			}
		})
	}
}
