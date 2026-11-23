package jobs

import (
	"encoding/json"
	"os"
	"testing"

	"content-creator-agent/internal/db"
	"github.com/stretchr/testify/require"
)

func TestSharedStructuredDocumentV2Contract(t *testing.T) {
	data, err := os.ReadFile("../../../../tests/fixtures/structured_documents_v2.json")
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
			_, err := validateDocumentV2(tc.Document, db.PostType(doc.PostType), len(doc.Slides))
			if tc.Valid {
				require.NoError(t, err)
			} else {
				require.Error(t, err)
			}
		})
	}
}

func TestV2DecorationOnlyAndImageAssetSet(t *testing.T) {
	data := []byte(`{"schemaVersion":2,"postType":"single","palette":{"background":"#ffffff","text":"#000000","accent":"#ffffff"},"slides":[{"id":"s1","layout":"hero","background":{"type":"solid","color":{"token":"background"}},"elements":[{"id":"d1","type":"decoration","kind":"line","color":{"hex":"#000000"},"width":"short","thickness":"thin","corner":"square"}]}]}`)
	used, err := validateDocumentV2(data, db.PostType("single"), 1)
	require.NoError(t, err)
	require.Empty(t, used)
	data = []byte(`{"schemaVersion":2,"postType":"single","palette":{"background":"#ffffff","text":"#000000","accent":"#ffffff"},"slides":[{"id":"s1","layout":"hero","background":{"type":"solid","color":{"token":"background"}},"elements":[{"id":"i1","type":"image","assetId":"asset-1","fit":"cover"}]}]}`)
	used, err = validateDocumentV2(data, db.PostType("single"), 1)
	require.NoError(t, err)
	require.Contains(t, used, "asset-1")
}
