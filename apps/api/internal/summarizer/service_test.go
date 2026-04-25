package summarizer

import (
	"context"
	"errors"
	"testing"
	"time"

	"content-creator-agent/internal/db"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

type mockSummRepo struct {
	eligible    []uuid.UUID
	byChat      map[uuid.UUID][]db.ChatContent
	upsertCalls int
	upsertErr   error
}

func (m *mockSummRepo) ListEligibleChatIDs(ctx context.Context) ([]uuid.UUID, error) {
	return m.eligible, nil
}

func (m *mockSummRepo) ListContentsOrdered(ctx context.Context, chatID uuid.UUID) ([]db.ChatContent, error) {
	if m.byChat == nil {
		return nil, nil
	}
	return m.byChat[chatID], nil
}

func (m *mockSummRepo) UpsertResume(ctx context.Context, chatID uuid.UUID, summary string, lastContentAt, summarizedAt time.Time) error {
	m.upsertCalls++
	return m.upsertErr
}

type mockSummClient struct {
	results []string
	errs    []error
	n       int
}

func (m *mockSummClient) Summarize(ctx context.Context, history string) (string, error) {
	i := m.n
	m.n++
	if i < len(m.errs) && m.errs[i] != nil {
		return "", m.errs[i]
	}
	if i < len(m.results) {
		return m.results[i], nil
	}
	return "", errors.New("unexpected Summarize call")
}

func TestRun_SkipsEmptyContents(t *testing.T) {
	cid := uuid.New()
	repo := &mockSummRepo{
		eligible: []uuid.UUID{cid},
		byChat:   map[uuid.UUID][]db.ChatContent{cid: {}},
	}
	oa := &mockSummClient{results: []string{"x"}}
	svc := &Service{repo: repo, openai: oa}
	svc.Run(context.Background())
	require.Equal(t, 0, oa.n)
	require.Equal(t, 0, repo.upsertCalls)
}

func TestRun_ErrorOnOneChat_ContinuesOthers(t *testing.T) {
	a := uuid.New()
	b := uuid.New()
	ts := time.Now().UTC()
	row := func(text string) []db.ChatContent {
		return []db.ChatContent{{Role: db.ChatContentRoleUser, Content: text, CreatedAt: ts}}
	}
	repo := &mockSummRepo{
		eligible: []uuid.UUID{a, b},
		byChat: map[uuid.UUID][]db.ChatContent{
			a: row("chat a"),
			b: row("chat b"),
		},
	}
	oa := &mockSummClient{
		errs:    []error{errors.New("openai down"), nil},
		results: []string{"", "summary b"},
	}
	svc := &Service{repo: repo, openai: oa}
	svc.Run(context.Background())
	require.Equal(t, 2, oa.n)
	require.Equal(t, 1, repo.upsertCalls)
}

func TestRun_EmptySummaryError(t *testing.T) {
	cid := uuid.New()
	ts := time.Now().UTC()
	repo := &mockSummRepo{
		eligible: []uuid.UUID{cid},
		byChat: map[uuid.UUID][]db.ChatContent{
			cid: {{Role: db.ChatContentRoleUser, Content: "hi", CreatedAt: ts}},
		},
	}
	oa := &mockSummClient{results: []string{""}}
	svc := &Service{repo: repo, openai: oa}
	svc.Run(context.Background())
	require.Equal(t, 1, oa.n)
	require.Equal(t, 0, repo.upsertCalls)
}
