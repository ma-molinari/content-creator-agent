package profile

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"path"
	"strings"
	"time"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/storage"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// ReferenceView is one design reference with a short-lived preview URL.
type ReferenceView struct {
	ID  uuid.UUID `json:"id"`
	URL string    `json:"url"`
}

// ProfileView is the API shape for GET /profile and PUT /profile.
type ProfileView struct {
	AuditText  string          `json:"auditText"`
	BrandText  string          `json:"brandText"`
	Configured bool            `json:"configured"`
	References []ReferenceView `json:"references"`
}

type store interface {
	GetByUserID(ctx context.Context, userID uuid.UUID) (*db.UserProfile, error)
	Upsert(ctx context.Context, userID uuid.UUID, auditText, brandText string) error
}

// Service handles profile reads, writes, and optional design references.
type Service struct {
	repo     store
	refRepo  *ReferencesRepository
	store    storage.StorageService
	maxRefs  int
	maxBytes int64
	preview  time.Duration
}

// NewService constructs a profile service. refRepo and store may be nil; reference features are disabled in that case.
func NewService(
	repo *Repository,
	refRepo *ReferencesRepository,
	store storage.StorageService,
	maxRefs int,
	maxBytes int64,
) *Service {
	if maxRefs <= 0 {
		maxRefs = 8
	}
	if maxBytes <= 0 {
		maxBytes = 5 * 1024 * 1024
	}
	return &Service{
		repo:     repo,
		refRepo:  refRepo,
		store:    store,
		maxRefs:  maxRefs,
		maxBytes: maxBytes,
		preview:  15 * time.Minute,
	}
}

func textsConfigured(audit, brand string) bool {
	return strings.TrimSpace(audit) != "" && strings.TrimSpace(brand) != ""
}

// GetProfile returns stored text, configuration flag, and reference previews.
func (s *Service) GetProfile(ctx context.Context, userID uuid.UUID) (ProfileView, error) {
	p, err := s.repo.GetByUserID(ctx, userID)
	if err != nil {
		return ProfileView{}, err
	}
	out := ProfileView{References: []ReferenceView{}}
	if p != nil {
		out.AuditText = p.AuditText
		out.BrandText = p.BrandText
		out.Configured = textsConfigured(p.AuditText, p.BrandText)
	}
	if s.refRepo == nil || s.store == nil {
		return out, nil
	}
	rows, err := s.refRepo.ListByUserID(ctx, userID)
	if err != nil {
		return ProfileView{}, err
	}
	for _, row := range rows {
		u, err := s.store.GetSignedURL(ctx, row.S3Key, s.preview)
		if err != nil {
			return ProfileView{}, err
		}
		out.References = append(out.References, ReferenceView{ID: row.ID, URL: u})
	}
	return out, nil
}

// SaveProfile persists audit and brand text (may be empty strings).
func (s *Service) SaveProfile(ctx context.Context, userID uuid.UUID, auditText, brandText string) error {
	return s.repo.Upsert(ctx, userID, auditText, brandText)
}

// ListReferenceS3Keys returns ordered S3 keys for worker dispatch.
func (s *Service) ListReferenceS3Keys(ctx context.Context, userID uuid.UUID) ([]string, error) {
	if s.refRepo == nil {
		return nil, nil
	}
	return s.refRepo.ListS3KeysByUserID(ctx, userID)
}

// Sentinel errors for reference uploads and deletes.
var (
	ErrProfileRefsNotAvailable = errors.New("profile: design references are not available")
	ErrTooManyProfileRefs      = errors.New("profile: maximum number of design references reached")
	ErrFileTooLarge            = errors.New("profile: file too large")
	ErrInvalidImageType        = errors.New("profile: invalid image type")
	ErrReferenceNotFound       = errors.New("profile: design reference not found")
)

// UploadReferenceImage validates, uploads to S3, and records the row. data must be at most s.maxBytes.
func (s *Service) UploadReferenceImage(ctx context.Context, userID uuid.UUID, data []byte, clientFilename, clientContentType string) error {
	if s.refRepo == nil || s.store == nil {
		return ErrProfileRefsNotAvailable
	}
	if int64(len(data)) > s.maxBytes {
		return fmt.Errorf("%w (max %d bytes)", ErrFileTooLarge, s.maxBytes)
	}
	if int64(len(data)) == 0 {
		return ErrInvalidImageType
	}
	n, err := s.refRepo.CountByUserID(ctx, userID)
	if err != nil {
		return err
	}
	if int(n) >= s.maxRefs {
		return fmt.Errorf("%w (max %d)", ErrTooManyProfileRefs, s.maxRefs)
	}

	ct := http.DetectContentType(data)
	decl := strings.TrimSpace(strings.Split(clientContentType, ";")[0])
	if decl != "" && decl != "application/octet-stream" {
		ct = decl
	}
	ext, ok := extForImageType(ct)
	if !ok {
		// Try extension from client filename
		_, e := extFromFilename(clientFilename)
		switch strings.ToLower(e) {
		case ".jpg", ".jpeg":
			ct, ext, ok = "image/jpeg", ".jpg", true
		case ".png":
			ct, ext, ok = "image/png", ".png", true
		case ".webp":
			ct, ext, ok = "image/webp", ".webp", true
		case ".gif":
			ct, ext, ok = "image/gif", ".gif", true
		}
	}
	if !ok || !allowedImageContentType(ct) {
		return ErrInvalidImageType
	}

	key := fmt.Sprintf("users/%s/design-refs/%s%s", userID, uuid.New().String(), ext)
	if err := s.store.Upload(ctx, key, data); err != nil {
		return err
	}
	_, err = s.refRepo.Create(ctx, userID, key)
	if err != nil {
		_ = s.store.Delete(ctx, key)
		return err
	}
	return nil
}

// DeleteReference removes one reference (DB + S3) for the user.
func (s *Service) DeleteReference(ctx context.Context, userID, refID uuid.UUID) error {
	if s.refRepo == nil || s.store == nil {
		return ErrProfileRefsNotAvailable
	}
	row, err := s.refRepo.GetByIDForUser(ctx, refID, userID)
	if err != nil {
		return err
	}
	if row == nil {
		return ErrReferenceNotFound
	}
	if err := s.store.Delete(ctx, row.S3Key); err != nil {
		return err
	}
	if err := s.refRepo.DeleteByIDForUser(ctx, refID, userID); err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return ErrReferenceNotFound
		}
		return err
	}
	return nil
}

// MaxReferenceBytes is the maximum allowed upload size (for handlers).
func (s *Service) MaxReferenceBytes() int64 { return s.maxBytes }

func allowedImageContentType(ct string) bool {
	switch strings.ToLower(ct) {
	case "image/jpeg", "image/png", "image/webp", "image/gif":
		return true
	default:
		return false
	}
}

func extForImageType(ct string) (ext string, ok bool) {
	switch strings.ToLower(ct) {
	case "image/jpeg":
		return ".jpg", true
	case "image/png":
		return ".png", true
	case "image/webp":
		return ".webp", true
	case "image/gif":
		return ".gif", true
	default:
		return "", false
	}
}

func extFromFilename(name string) (base, ext string) {
	return strings.TrimSuffix(name, path.Ext(name)), path.Ext(name)
}
