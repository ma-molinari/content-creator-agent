//go:build integration

package integration

import (
	"bytes"
	"context"
	"log"
	"strings"
	"testing"
	"time"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

func TestWatchdogRecordsTerminalEventsByFormat(t *testing.T) {
	env := newTestEnv(t, nil)
	uid := uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: uid, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", uid) })
	old := time.Now().UTC().Add(-2 * time.Hour)
	for _, format := range []db.PostFormat{db.PostFormatLegacy, db.PostFormatStructuredV1} {
		chatID := uuid.New()
		require.NoError(t, env.DB.Create(&db.Chat{ID: chatID, UserID: uid, PostType: db.PostTypeSingle, PostFormat: format}).Error)
		require.NoError(t, env.DB.Create(&db.Job{ID: uuid.New(), ChatID: chatID, UserID: uid, Status: db.JobStatusProcessing, PostFormat: format, CreatedAt: old, UpdatedAt: old}).Error)
	}
	original := log.Writer()
	var output bytes.Buffer
	log.SetOutput(&output)
	t.Cleanup(func() { log.SetOutput(original) })
	cutoff := time.Now().UTC().Add(-time.Hour)
	repo := jobs.NewRepository(env.DB)
	n, err := repo.FailStuckProcessingJobs(context.Background(), cutoff, jobs.StuckJobErrorMsg)
	require.NoError(t, err)
	require.EqualValues(t, 2, n)
	n, err = repo.FailStuckProcessingJobs(context.Background(), cutoff, jobs.StuckJobErrorMsg)
	require.NoError(t, err)
	require.Zero(t, n)
	require.Equal(t, 2, strings.Count(output.String(), "event=job_terminal"))
	require.Contains(t, output.String(), "format=legacy_html")
	require.Contains(t, output.String(), "format=structured_v1")
	require.Contains(t, output.String(), "code=STUCK_PROCESSING")
}
