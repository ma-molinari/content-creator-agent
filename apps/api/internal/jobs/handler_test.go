package jobs

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"content-creator-agent/internal/config"
	"content-creator-agent/internal/db"
	"content-creator-agent/internal/storage"

	"github.com/google/uuid"
	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/require"
)

type artifactMissingHeadStore struct{}

func (artifactMissingHeadStore) Upload(context.Context, string, []byte) error { return nil }

func (artifactMissingHeadStore) GetSignedURL(context.Context, string, time.Duration) (string, error) {
	return "https://example.com/signed", nil
}

func (artifactMissingHeadStore) HeadObject(context.Context, string) error {
	return fmt.Errorf("mock: %w", storage.ErrObjectNotFound)
}

func (artifactMissingHeadStore) GetObject(context.Context, string) ([]byte, error) { return nil, nil }

func (artifactMissingHeadStore) Delete(context.Context, string) error { return nil }

func (artifactMissingHeadStore) DeleteMany(context.Context, []string) error { return nil }

func TestHandler_Complete_returns400WhenArtifactMissingInStorage(t *testing.T) {
	gdb := testCompleteSchemaDB(t)
	cfg := &config.Config{WorkerAPIKey: "k"}
	h := NewHandler(cfg, gdb, artifactMissingHeadStore{})

	jobID := uuid.New()
	chatID := uuid.New()
	userID := uuid.New()
	now := time.Now().UTC()
	require.NoError(t, gdb.Create(&db.Chat{
		ID:        chatID,
		UserID:    userID,
		PostType:  db.PostTypeSingle,
		CreatedAt: now,
		UpdatedAt: now,
	}).Error)
	require.NoError(t, gdb.Create(&db.Job{
		ID:        jobID,
		ChatID:    chatID,
		UserID:    userID,
		Status:    db.JobStatusProcessing,
		CreatedAt: now,
		UpdatedAt: now,
	}).Error)

	key := "slides/" + jobID.String() + "/slide-1.jpg"
	body := map[string]any{
		"assistantText": "hi",
		"artifacts": []map[string]any{
			{"s3Key": key, "slideNumber": 1},
		},
	}
	raw, err := json.Marshal(body)
	require.NoError(t, err)

	e := echo.New()
	req := httptest.NewRequest(http.MethodPost, "/", bytes.NewReader(raw))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	req.Header.Set("X-Worker-API-Key", "k")
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)
	c.SetPath("/internal/jobs/:id/complete")
	c.SetParamNames("id")
	c.SetParamValues(jobID.String())

	err = h.Complete(c)
	var he *echo.HTTPError
	require.ErrorAs(t, err, &he)
	require.Equal(t, http.StatusBadRequest, he.Code)
	msg, ok := he.Message.(map[string]string)
	require.True(t, ok)
	require.Contains(t, msg["message"], "Artefato")
}
