package jobs

import (
	"context"
	"mime"
	"strings"
	"time"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/storage"
	"github.com/google/uuid"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

const maxStructuredDocumentBytes int64 = 2 * 1024 * 1024

type boundedDocumentStore interface {
	GetObjectLimited(ctx context.Context, key string, maxBytes int64) ([]byte, string, error)
}

func validateStructuredDocument(ctx context.Context, store storage.StorageService, key string, postType db.PostType, slideCount int) (map[string]struct{}, error) {
	return validateStructuredDocumentVersion(ctx, store, key, postType, slideCount, 1)
}

func validateStructuredDocumentVersion(ctx context.Context, store storage.StorageService, key string, postType db.PostType, slideCount, schemaVersion int) (map[string]struct{}, error) {
	bounded, ok := store.(boundedDocumentStore)
	if !ok {
		return nil, gorm.ErrInvalidData
	}
	data, contentType, err := bounded.GetObjectLimited(ctx, key, maxStructuredDocumentBytes)
	if err != nil {
		if storage.IsObjectNotFound(err) {
			return nil, ErrArtifactObjectNotFound
		}
		return nil, err
	}
	mediaType, _, err := mime.ParseMediaType(contentType)
	if err != nil || mediaType != "application/json" || int64(len(data)) > maxStructuredDocumentBytes {
		return nil, gorm.ErrInvalidData
	}
	switch schemaVersion {
	case 1:
		return validateDocumentV1(data, postType, slideCount)
	case 2:
		return validateDocumentV2(data, postType, slideCount)
	case 3:
		return validateDocumentV3(data, postType, slideCount)
	default:
		return nil, gorm.ErrInvalidData
	}
}

type StructuredArtifact struct {
	DocumentS3Key   string `json:"documentS3Key"`
	SchemaVersion   int    `json:"schemaVersion"`
	RendererVersion string `json:"rendererVersion"`
}

// CompleteStructuredReply publishes a version only if the job still targets the current base.
// A detected conflict is committed as a terminal job status before returning conflict=true.
func CompleteStructuredReply(ctx context.Context, gdb *gorm.DB, jobID uuid.UUID, text string, artifacts []ArtifactRef, source StructuredArtifact, store storage.StorageService) (alreadyDone, conflict bool, err error) {
	var probe db.Job
	if err := gdb.WithContext(ctx).Select("id", "chat_id").First(&probe, "id = ?", jobID).Error; err != nil {
		return false, false, err
	}
	err = gdb.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		// Always lock the chat before the job, including when the current version is nil.
		var chat db.Chat
		if e := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&chat, "id = ?", probe.ChatID).Error; e != nil {
			return e
		}
		var job db.Job
		if e := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&job, "id = ? AND chat_id = ?", jobID, chat.ID).Error; e != nil {
			return e
		}
		if job.PostFormat != db.PostFormatStructuredV1 || chat.PostFormat != db.PostFormatStructuredV1 {
			return gorm.ErrInvalidData
		}
		if job.Status == db.JobStatusDone {
			alreadyDone = true
			return nil
		}
		if job.Status == db.JobStatusFailed {
			return ErrJobCompleteConflict
		}
		if job.Status != db.JobStatusProcessing {
			return ErrJobNotProcessing
		}
		sameBase := (chat.CurrentVersionID == nil && job.ExpectedVersionID == nil) ||
			(chat.CurrentVersionID != nil && job.ExpectedVersionID != nil && *chat.CurrentVersionID == *job.ExpectedVersionID)
		if !sameBase {
			conflict = true
			return tx.Model(&db.Job{}).Where("id = ?", job.ID).Updates(map[string]interface{}{
				"status": db.JobStatusFailed, "stage": "failed", "progress": 100,
				"error_code": "VERSION_CONFLICT", "error_msg": "A versão do post mudou. Atualize o chat antes de tentar novamente.", "updated_at": time.Now().UTC(),
			}).Error
		}
		if job.GenerationMode == nil || (*job.GenerationMode != "create" && *job.GenerationMode != "edit") || (*job.GenerationMode == "edit" && job.ExpectedVersionID == nil) {
			return gorm.ErrInvalidData
		}
		key := strings.TrimSpace(source.DocumentS3Key)
		target := job.StructuredTargetSchema()
		if key != "slides/"+job.ID.String()+"/document.json" || (target != 1 && target != 2 && target != 3) || source.SchemaVersion != target || strings.TrimSpace(source.RendererVersion) == "" || len(strings.TrimSpace(source.RendererVersion)) > 64 || len(artifacts) == 0 || len(artifacts) > 20 || (chat.PostType == db.PostTypeSingle && len(artifacts) != 1) {
			return gorm.ErrInvalidData
		}
		if e := validateSlideArtifactKey(job.ID, key); e != nil {
			return e
		}
		usedAssets, e := validateStructuredDocumentVersion(ctx, store, key, chat.PostType, len(artifacts), target)
		if e != nil {
			return e
		}
		bounded, ok := store.(boundedDocumentStore)
		if !ok {
			return gorm.ErrInvalidData
		}
		manifest, contentType, e := bounded.GetObjectLimited(ctx, "slides/"+job.ID.String()+"/assets.json", storage.MaxAssetManifestBytes)
		if e != nil {
			if storage.IsObjectNotFound(e) {
				return ErrArtifactObjectNotFound
			}
			return e
		}
		mediaType, _, e := mime.ParseMediaType(contentType)
		if e != nil || mediaType != "application/json" {
			return gorm.ErrInvalidData
		}
		assetKeys, e := storage.ValidateAssetManifest(manifest, job.ID)
		if e != nil {
			return gorm.ErrInvalidData
		}
		if len(usedAssets) != len(assetKeys) {
			return gorm.ErrInvalidData
		}
		for id := range usedAssets {
			if _, ok := assetKeys[id]; !ok {
				return gorm.ErrInvalidData
			}
		}
		for _, assetKey := range assetKeys {
			if e := store.HeadObject(ctx, assetKey); e != nil {
				if storage.IsObjectNotFound(e) {
					return ErrArtifactObjectNotFound
				}
				return e
			}
		}

		seen := map[int]bool{}
		for _, a := range artifacts {
			if a.SlideNumber <= 0 || a.SlideNumber > len(artifacts) || seen[a.SlideNumber] || a.HtmlS3Key == nil || !strings.HasSuffix(strings.ToLower(strings.TrimSpace(*a.HtmlS3Key)), ".html") || !strings.HasSuffix(strings.ToLower(strings.TrimSpace(a.S3Key)), ".jpeg") {
				return gorm.ErrInvalidData
			}
			seen[a.SlideNumber] = true
		}
		if e := ensureSlideArtifactsExist(ctx, job.ID, artifacts, store); e != nil {
			return e
		}
		assistant := db.ChatContent{ID: uuid.New(), ChatID: chat.ID, Role: db.ChatContentRoleAssistant, Content: text}
		if e := tx.Create(&assistant).Error; e != nil {
			return e
		}
		for _, a := range artifacts {
			url, e := store.GetSignedURL(ctx, a.S3Key, signedURLExpiry)
			if e != nil {
				return e
			}
			img := db.ChatContentImage{ID: uuid.New(), ChatContentID: assistant.ID, S3Key: a.S3Key, HtmlS3Key: a.HtmlS3Key, URL: url, SlideNumber: a.SlideNumber}
			if e := tx.Create(&img).Error; e != nil {
				return e
			}
		}
		var parent *uuid.UUID
		if *job.GenerationMode == "edit" {
			parent = job.ExpectedVersionID
		}
		version := db.PostVersion{ID: uuid.New(), ChatID: chat.ID, JobID: job.ID, AssistantContentID: assistant.ID, ParentVersionID: parent, DocumentS3Key: key, SchemaVersion: source.SchemaVersion, RendererVersion: strings.TrimSpace(source.RendererVersion)}
		if e := tx.Create(&version).Error; e != nil {
			return e
		}
		if e := tx.Model(&db.Chat{}).Where("id = ?", chat.ID).Update("current_version_id", version.ID).Error; e != nil {
			return e
		}
		return tx.Model(&db.Job{}).Where("id = ?", job.ID).Updates(map[string]interface{}{"status": db.JobStatusDone, "stage": "done", "progress": 100, "error_msg": nil, "error_code": nil, "heartbeat_at": time.Now().UTC(), "updated_at": time.Now().UTC()}).Error
	})
	return alreadyDone, conflict, err
}
