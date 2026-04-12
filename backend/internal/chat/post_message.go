package chat

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"content-creator-agent/internal/agent"
	"content-creator-agent/internal/db"
	"content-creator-agent/internal/export"

	"github.com/google/uuid"
)

// AgentDeps wires profile checks, LLM pipeline, and Playwright export.
type AgentDeps struct {
	Profile   *agent.ProfileChecker
	Optimizer *agent.PromptOptimizer
	SlideGen  *agent.SlideGenerator
	Runner    *export.PlaywrightRunner
}

// PostMessageResult is the outcome of POST /chats/:id/messages.
type PostMessageResult struct {
	Assistant *db.ChatContent
	Images    []db.ChatContentImage
	Files     []FileListItem
}

var slideJPGNum = regexp.MustCompile(`(?i)slide-(\d+)\.jpg`)

// PostMessage runs optimize → generate slides → export → S3 → persist.
func (s *Service) PostMessage(ctx context.Context, userID, chatID uuid.UUID, body string) (*PostMessageResult, error) {
	if s.agent == nil || s.agent.Optimizer == nil || s.agent.SlideGen == nil || s.agent.Runner == nil || s.agent.Profile == nil {
		return nil, ErrAgentNotConfigured
	}
	if err := s.assertChatOwner(ctx, userID, chatID); err != nil {
		return nil, err
	}
	ok, err := s.agent.Profile.CheckProfileSetup(ctx, userID)
	if err != nil {
		return nil, err
	}
	if !ok {
		return nil, agent.ErrSetupRequired
	}
	profileText, err := s.agent.Profile.LoadProfileText(ctx, userID)
	if err != nil {
		return nil, err
	}
	history, err := s.buildRepromptContext(ctx, chatID)
	if err != nil {
		return nil, err
	}
	userProfile := profileText
	if history != "" {
		userProfile += "\n\nContexto da conversa:\n" + history
	}
	optimized, err := s.agent.Optimizer.OptimizePrompt(ctx, body, userProfile)
	if err != nil {
		return nil, err
	}
	slides, err := s.agent.SlideGen.GenerateSlides(ctx, userID, optimized)
	if err != nil {
		return nil, err
	}
	tmpDir, err := os.MkdirTemp("", "carousel-*")
	if err != nil {
		return nil, fmt.Errorf("chat: temp dir: %w", err)
	}
	success := false
	defer func() {
		if success {
			_ = os.RemoveAll(tmpDir)
		}
	}()
	for i, sl := range slides {
		name := sl.Name
		if name == "" {
			name = fmt.Sprintf("slide-%02d.html", i+1)
		}
		path := filepath.Join(tmpDir, filepath.Base(name))
		if err := os.WriteFile(path, []byte(sl.HTML), 0o600); err != nil {
			return nil, fmt.Errorf("chat: write slide html: %w", err)
		}
	}
	if err := s.agent.Runner.ExportJPEGs(ctx, tmpDir); err != nil {
		return nil, fmt.Errorf("%w: %v", ErrExportFailed, err)
	}
	jpegs, err := listJPEGsOrdered(tmpDir)
	if err != nil || len(jpegs) == 0 {
		return nil, fmt.Errorf("%w: no jpeg output", ErrExportFailed)
	}
	userMsg := &db.ChatContent{
		ID:      uuid.New(),
		ChatID:  chatID,
		Role:    db.ChatContentRoleUser,
		Content: body,
	}
	asst := &db.ChatContent{
		ID:      uuid.New(),
		ChatID:  chatID,
		Role:    db.ChatContentRoleAssistant,
		Content: fmt.Sprintf("Carrossel gerado com %d slide(s).", len(jpegs)),
	}
	imgs := make([]db.ChatContentImage, 0, len(jpegs))
	files := make([]FileListItem, 0, len(jpegs))
	for _, jp := range jpegs {
		n := slideNumberFromJPEG(filepath.Base(jp))
		if n < 1 {
			continue
		}
		data, err := os.ReadFile(jp)
		if err != nil {
			return nil, fmt.Errorf("chat: read jpeg: %w", err)
		}
		key := fmt.Sprintf("users/%s/chats/%s/slide-%02d.jpg", userID.String(), chatID.String(), n)
		if err := s.store.Upload(ctx, key, data); err != nil {
			return nil, err
		}
		url, err := s.store.GetSignedURL(ctx, key, signedURLExpiry)
		if err != nil {
			return nil, err
		}
		imgRow := db.ChatContentImage{
			ID:          uuid.New(),
			S3Key:       key,
			URL:         url,
			SlideNumber: n,
		}
		imgs = append(imgs, imgRow)
		files = append(files, FileListItem{
			ID:          imgRow.ID,
			FileName:    fmt.Sprintf("slide-%d.jpg", n),
			MimeType:    "image/jpeg",
			DownloadURL: url,
		})
	}
	if err := s.repo.CreateContentWithImages(ctx, userMsg, asst, imgs); err != nil {
		return nil, err
	}
	// Refresh IDs on image rows for response
	for i := range imgs {
		imgs[i].ChatContentID = asst.ID
	}
	success = true
	return &PostMessageResult{Assistant: asst, Images: imgs, Files: files}, nil
}

func (s *Service) buildRepromptContext(ctx context.Context, chatID uuid.UUID) (string, error) {
	res, err := s.repo.GetResumeByChatID(ctx, chatID)
	if err != nil {
		return "", err
	}
	if res != nil && res.Summary != nil && strings.TrimSpace(*res.Summary) != "" {
		return strings.TrimSpace(*res.Summary), nil
	}
	contents, err := s.repo.ListContentsOrdered(ctx, chatID)
	if err != nil {
		return "", err
	}
	var b strings.Builder
	for _, c := range contents {
		b.WriteString(string(c.Role))
		b.WriteString(": ")
		b.WriteString(c.Content)
		b.WriteString("\n")
	}
	return strings.TrimSpace(b.String()), nil
}

func listJPEGsOrdered(dir string) ([]string, error) {
	matches, err := filepath.Glob(filepath.Join(dir, "slide-*.jpg"))
	if err != nil {
		return nil, err
	}
	sort.Slice(matches, func(i, j int) bool {
		return slideNumberFromJPEG(filepath.Base(matches[i])) < slideNumberFromJPEG(filepath.Base(matches[j]))
	})
	return matches, nil
}

func slideNumberFromJPEG(base string) int {
	m := slideJPGNum.FindStringSubmatch(base)
	if len(m) < 2 {
		return 0
	}
	n, _ := strconv.Atoi(m[1])
	return n
}

// IsProfileConfigured exposes profile setup status for GET /setup/status.
func (s *Service) IsProfileConfigured(ctx context.Context, userID uuid.UUID) (bool, error) {
	if s.agent == nil || s.agent.Profile == nil {
		return false, nil
	}
	return s.agent.Profile.CheckProfileSetup(ctx, userID)
}
