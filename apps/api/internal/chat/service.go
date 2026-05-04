package chat

import (
	"archive/zip"
	"bytes"
	"context"
	"errors"
	"fmt"
	"time"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"content-creator-agent/internal/profile"
	"content-creator-agent/internal/storage"

	"github.com/google/uuid"
)

// Sentinel errors mapped to HTTP in handlers.
var (
	ErrNotFound             = errors.New("chat: not found")
	ErrForbidden            = errors.New("chat: forbidden")
	ErrNoFiles              = errors.New("chat: no files to zip")
	ErrBadPostType          = errors.New("chat: invalid post type")
	ErrWorkerNotConfigured  = errors.New("chat: worker not configured")
	ErrSetupRequired        = errors.New("chat: profile setup required (audit and brand in app)")
	ErrEmptyPrompt          = errors.New("chat: empty prompt after sanitization")
	ErrWorkerDispatchFailed = errors.New("chat: worker dispatch failed")
	// ErrSlideStorageNotFound means the DB references an S3 key with no object (orphan or misconfigured bucket).
	ErrSlideStorageNotFound = errors.New("chat: slide file missing in storage")
)

const listChatsLimit = 5
const signedURLExpiry = time.Hour

// Service coordinates chat use cases and storage.
type Service struct {
	repo        *Repository
	jobsRepo    *jobs.Repository
	store       storage.StorageService
	profileRepo *profile.Repository
	profileSvc  *profile.Service
	worker      jobs.WorkerClient

	// latestAssistantHTMLKeys defaults to repo.GetLatestAssistantHTMLKeys; tests may replace it to simulate failures.
	latestAssistantHTMLKeys func(context.Context, uuid.UUID) ([]string, error)
}

// NewService constructs a chat service. worker may be nil (message routes unavailable).
// profileRepo may be nil (profile checks and message dispatch then behave as setup-required).
// profileSvc may be nil; when set, its reference S3 keys are sent on job dispatch.
// Profile copy lives in the database only (PUT /profile); there is no disk fallback.
func NewService(repo *Repository, jobsRepo *jobs.Repository, store storage.StorageService, profileRepo *profile.Repository, profileSvc *profile.Service, worker jobs.WorkerClient) *Service {
	svc := &Service{repo: repo, jobsRepo: jobsRepo, store: store, profileRepo: profileRepo, profileSvc: profileSvc, worker: worker}
	if repo != nil {
		svc.latestAssistantHTMLKeys = repo.GetLatestAssistantHTMLKeys
	}
	return svc
}

// ListChats returns up to 5 chats for the user.
func (s *Service) ListChats(ctx context.Context, userID uuid.UUID) ([]db.Chat, error) {
	return s.repo.ListByUser(ctx, userID, listChatsLimit)
}

// CreateChat creates a chat, evicting the oldest when the user already has 5.
// The count-check and insert run in a single transaction to prevent TOCTOU races.
func (s *Service) CreateChat(ctx context.Context, userID uuid.UUID, postType string) (*db.Chat, error) {
	pt, err := parsePostType(postType)
	if err != nil {
		return nil, err
	}
	created, evictedID, err := s.repo.CreateChatEvicting(ctx, userID, pt, listChatsLimit)
	if err != nil {
		return nil, err
	}
	// S3 cleanup of evicted chat happens outside the transaction (best-effort).
	if evictedID != nil {
		keys, err := s.repo.CollectS3KeysForChat(ctx, *evictedID)
		if err == nil {
			_ = s.store.DeleteMany(ctx, keys)
		}
	}
	return created, nil
}

func parsePostType(s string) (db.PostType, error) {
	switch db.PostType(s) {
	case db.PostTypeSingle, db.PostTypeCarousel:
		return db.PostType(s), nil
	default:
		return "", fmt.Errorf("%w: %q", ErrBadPostType, s)
	}
}

// GetChat returns a chat with contents when the user owns it.
func (s *Service) GetChat(ctx context.Context, userID, chatID uuid.UUID) (*db.Chat, error) {
	c, err := s.repo.GetByIDWithContents(ctx, chatID)
	if ErrRecordNotFound(err) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	if c.UserID != userID {
		return nil, ErrForbidden
	}
	if err := s.refreshContentImageURLs(ctx, c); err != nil {
		return nil, err
	}
	return c, nil
}

func (s *Service) refreshContentImageURLs(ctx context.Context, c *db.Chat) error {
	for i := range c.Contents {
		for j := range c.Contents[i].Images {
			url, err := s.store.GetSignedURL(ctx, c.Contents[i].Images[j].S3Key, signedURLExpiry)
			if err != nil {
				return err
			}
			c.Contents[i].Images[j].URL = url
		}
	}
	return nil
}

// DeleteChat removes S3 objects then the chat row.
func (s *Service) DeleteChat(ctx context.Context, userID, chatID uuid.UUID) error {
	c, err := s.repo.GetByID(ctx, chatID)
	if ErrRecordNotFound(err) {
		return ErrNotFound
	}
	if err != nil {
		return err
	}
	if c.UserID != userID {
		return ErrForbidden
	}
	keys, err := s.repo.CollectS3KeysForChat(ctx, chatID)
	if err != nil {
		return err
	}
	if err := s.store.DeleteMany(ctx, keys); err != nil {
		return err
	}
	if err := s.repo.DeleteChat(ctx, chatID); err != nil {
		return err
	}
	return nil
}

// FileListItem is one generated slide with a presigned download URL.
type FileListItem struct {
	ID          uuid.UUID `json:"id"`
	FileName    string    `json:"fileName"`
	MimeType    string    `json:"mimeType"`
	DownloadURL string    `json:"downloadUrl"`
}

// ListFiles returns signed URLs for all images in the chat.
func (s *Service) ListFiles(ctx context.Context, userID, chatID uuid.UUID) ([]FileListItem, error) {
	if err := s.assertChatOwner(ctx, userID, chatID); err != nil {
		return nil, err
	}
	imgs, err := s.repo.ListImagesForChat(ctx, chatID)
	if err != nil {
		return nil, err
	}
	out := make([]FileListItem, 0, len(imgs))
	for _, img := range imgs {
		url, err := s.store.GetSignedURL(ctx, img.S3Key, signedURLExpiry)
		if err != nil {
			return nil, err
		}
		out = append(out, FileListItem{
			ID:          img.ID,
			FileName:    imageArchiveFileName(img),
			MimeType:    "image/jpeg",
			DownloadURL: url,
		})
	}
	return out, nil
}

// BuildChatZip downloads all JPEGs and returns a zip in memory.
func (s *Service) BuildChatZip(ctx context.Context, userID, chatID uuid.UUID) ([]byte, string, error) {
	if err := s.assertChatOwner(ctx, userID, chatID); err != nil {
		return nil, "", err
	}
	imgs, err := s.repo.ListImagesForChat(ctx, chatID)
	if err != nil {
		return nil, "", err
	}
	if len(imgs) == 0 {
		return nil, "", ErrNoFiles
	}
	buf := new(bytes.Buffer)
	zw := zip.NewWriter(buf)
	for _, img := range imgs {
		data, err := s.store.GetObject(ctx, img.S3Key)
		if err != nil {
			_ = zw.Close()
			if storage.IsObjectNotFound(err) {
				return nil, "", ErrSlideStorageNotFound
			}
			return nil, "", err
		}
		w, err := zw.Create(imageArchiveFileName(img))
		if err != nil {
			_ = zw.Close()
			return nil, "", err
		}
		if _, err := w.Write(data); err != nil {
			_ = zw.Close()
			return nil, "", err
		}
	}
	if err := zw.Close(); err != nil {
		return nil, "", err
	}
	filename := fmt.Sprintf("slides-%s.zip", chatID.String())
	return buf.Bytes(), filename, nil
}

// BuildContentZip builds a ZIP of JPEG slides for one assistant turn (contentId).
func (s *Service) BuildContentZip(ctx context.Context, userID, chatID, contentID uuid.UUID) ([]byte, string, error) {
	if err := s.assertChatOwner(ctx, userID, chatID); err != nil {
		return nil, "", err
	}
	imgs, err := s.repo.ListImagesForContent(ctx, chatID, contentID)
	if err != nil {
		return nil, "", err
	}
	if len(imgs) == 0 {
		return nil, "", ErrNoFiles
	}
	buf := new(bytes.Buffer)
	zw := zip.NewWriter(buf)
	for _, img := range imgs {
		data, err := s.store.GetObject(ctx, img.S3Key)
		if err != nil {
			_ = zw.Close()
			if storage.IsObjectNotFound(err) {
				return nil, "", ErrSlideStorageNotFound
			}
			return nil, "", err
		}
		w, err := zw.Create(imageArchiveFileName(img))
		if err != nil {
			_ = zw.Close()
			return nil, "", err
		}
		if _, err := w.Write(data); err != nil {
			_ = zw.Close()
			return nil, "", err
		}
	}
	if err := zw.Close(); err != nil {
		return nil, "", err
	}
	filename := fmt.Sprintf("slides-%s.zip", contentID.String())
	return buf.Bytes(), filename, nil
}

// GetImageJPEG returns raw JPEG bytes when the file belongs to the user's chat.
func (s *Service) GetImageJPEG(ctx context.Context, userID, chatID, fileID uuid.UUID) ([]byte, error) {
	c, err := s.repo.GetByID(ctx, chatID)
	if ErrRecordNotFound(err) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	if c.UserID != userID {
		return nil, ErrForbidden
	}
	img, err := s.repo.GetImageInChat(ctx, chatID, fileID)
	if ErrRecordNotFound(err) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	data, err := s.store.GetObject(ctx, img.S3Key)
	if err != nil && storage.IsObjectNotFound(err) {
		return nil, ErrSlideStorageNotFound
	}
	return data, err
}

// getChatIfOwner loads the chat when it exists and belongs to userID.
func (s *Service) getChatIfOwner(ctx context.Context, userID, chatID uuid.UUID) (*db.Chat, error) {
	c, err := s.repo.GetByID(ctx, chatID)
	if ErrRecordNotFound(err) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	if c.UserID != userID {
		return nil, ErrForbidden
	}
	return c, nil
}

func (s *Service) assertChatOwner(ctx context.Context, userID, chatID uuid.UUID) error {
	_, err := s.getChatIfOwner(ctx, userID, chatID)
	return err
}

// imageArchiveFileName is the path used in ZIPs and ListFiles: one folder per assistant
// message (chat_content id) so slide numbers can repeat across turns without collision.
func imageArchiveFileName(img db.ChatContentImage) string {
	return fmt.Sprintf("%s/slide-%d.jpg", img.ChatContentID.String(), img.SlideNumber)
}
