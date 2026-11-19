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
	lowercaseCode := "prompt_rejected"
	require.Equal(t, lowercaseCode, metricErrorCode(&lowercaseCode))
	require.Equal(t, "UNSPECIFIED", metricErrorCode(nil))
}

func TestTerminalEventSanitizesVersionAndStage(t *testing.T) {
	original := log.Writer()
	var output bytes.Buffer
	log.SetOutput(&output)
	t.Cleanup(func() { log.SetOutput(original) })
	job := db.Job{ID: uuid.New(), ChatID: uuid.New(), Stage: "done", PostFormat: db.PostFormatStructuredV1, CreatedAt: time.Now()}
	logTerminalJob(job, "done", "NONE", &db.PostVersion{SchemaVersion: 1, RendererVersion: "1.0.0"})
	require.Contains(t, output.String(), "chat_id="+job.ChatID.String())
	require.Contains(t, output.String(), "stage=done")
	require.Contains(t, output.String(), "schema_version=1 renderer_version=1.0.0")
	output.Reset()
	job.Stage = "secret\nINJECTED"
	logTerminalJob(job, "done", "NONE", &db.PostVersion{SchemaVersion: 1, RendererVersion: "secret\nINJECTED"})
	require.Contains(t, output.String(), "stage=UNSPECIFIED")
	require.Contains(t, output.String(), "schema_version=unknown renderer_version=unknown")
	require.NotContains(t, output.String(), "secret")
}
