package jobs

import (
	"bytes"
	"context"
	"log"
	"testing"
	"time"

	"content-creator-agent/internal/db"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

func TestJobOutcomeLogsSafeFields(t *testing.T) {
	gdb := testCompleteSchemaDB(t)
	userID, chatID, jobID := uuid.New(), uuid.New(), uuid.New()
	require.NoError(t, gdb.Create(&db.Chat{ID: chatID, UserID: userID, PostType: db.PostTypeSingle}).Error)
	require.NoError(t, gdb.Create(&db.Job{ID: jobID, ChatID: chatID, UserID: userID, Status: db.JobStatusProcessing, PostFormat: db.PostFormatStructuredV1, CreatedAt: time.Now().Add(-time.Second)}).Error)
	original := log.Writer()
	var output bytes.Buffer
	log.SetOutput(&output)
	t.Cleanup(func() { log.SetOutput(original) })
	unsafe := "SECRET\nINJECTED=1"
	logJobOutcome(context.Background(), gdb, jobID, "failed", metricErrorCode(&unsafe))
	require.Contains(t, output.String(), "event=job_terminal")
	require.Contains(t, output.String(), "format=structured_v1")
	require.Contains(t, output.String(), "outcome=failed")
	require.Contains(t, output.String(), "code=UNSPECIFIED")
	require.Contains(t, output.String(), "duration_ms=")
	require.NotContains(t, output.String(), "SECRET")
	code := "VERSION_CONFLICT"
	require.Equal(t, code, metricErrorCode(&code))
	require.Equal(t, "UNSPECIFIED", metricErrorCode(nil))
}
