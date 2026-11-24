package jobs

import (
	"context"
	"strings"
	"testing"

	"content-creator-agent/internal/db"
	"github.com/stretchr/testify/require"
)

func TestValidateDocumentV3(t *testing.T) {
	doc := `{"schemaVersion":3,"postType":"single","palette":{"background":"#FFFFFF","text":"#000000","accent":"#000000"},"slides":[{"id":"s1","layout":"hero","background":{"type":"image","assetId":"photo"},"elements":[{"id":"t1","type":"text","role":"heading","content":"Olá","style":{"color":{"token":"text"},"size":"large"}}]}],"credits":{"photo":{"title":"Paisagem","creator":"Fotógrafa","sourceUrl":"https://commons.wikimedia.org/wiki/File:Example","license":"cc0","licenseUrl":"https://creativecommons.org/publicdomain/zero/1.0/"}}}`
	assets, err := validateDocumentV3([]byte(doc), db.PostTypeSingle, 1)
	require.NoError(t, err)
	require.Contains(t, assets, "photo")
	assets, err = validateStructuredDocumentVersion(context.Background(), documentStore{data: []byte(doc), contentType: "application/json"}, "test", db.PostTypeSingle, 1, 3)
	require.NoError(t, err)
	require.Contains(t, assets, "photo")
	for _, invalid := range []string{
		strings.Replace(doc, `"photo":{"title"`, `"other":{"title"`, 1),
		strings.Replace(doc, `https://commons.wikimedia.org/wiki/File:Example`, `javascript:alert(1)`, 1),
		strings.Replace(doc, `"license":"cc0"`, `"license":"by-nc"`, 1),
		strings.Replace(doc, `"assetId":"photo"`, `"assetId":"../other"`, 1),
	} {
		_, err := validateDocumentV3([]byte(invalid), db.PostTypeSingle, 1)
		require.Error(t, err)
	}
}
