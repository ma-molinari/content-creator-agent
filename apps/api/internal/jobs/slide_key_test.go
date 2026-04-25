package jobs

import (
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

func TestValidateSlideArtifactKey(t *testing.T) {
	id := uuid.MustParse("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
	prefix := "slides/" + id.String() + "/"

	require.NoError(t, validateSlideArtifactKey(id, prefix+"slide1.jpg"))
	require.ErrorIs(t, validateSlideArtifactKey(id, "other/"+id.String()+"/slide1.jpg"), ErrInvalidSlideS3Key)
	require.ErrorIs(t, validateSlideArtifactKey(id, prefix+"../x.jpg"), ErrInvalidSlideS3Key)
	require.ErrorIs(t, validateSlideArtifactKey(id, prefix), ErrInvalidSlideS3Key)
	other := uuid.MustParse("6ba7b811-9dad-11d1-80b4-00c04fd430c8")
	require.ErrorIs(t, validateSlideArtifactKey(id, "slides/"+other.String()+"/a.jpg"), ErrInvalidSlideS3Key)
}
