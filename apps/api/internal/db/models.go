package db

import (
	"time"

	"github.com/google/uuid"
)

type Role string

const (
	RoleUser  Role = "user"
	RoleAdmin Role = "admin"
)

type PostType string

const (
	PostTypeSingle   PostType = "single"
	PostTypeCarousel PostType = "carousel"
)

type ChatContentRole string

const (
	ChatContentRoleUser      ChatContentRole = "user"
	ChatContentRoleAssistant ChatContentRole = "assistant"
)

type User struct {
	ID              uuid.UUID `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
	Email           string    `gorm:"uniqueIndex;size:255;not null"`
	PasswordHash    string    `gorm:"column:password_hash;not null"`
	SecurityKeyHash string    `gorm:"column:security_key_hash;not null"`
	Role            Role      `gorm:"type:role_enum;not null;default:user"`
	CreatedAt       time.Time
	UpdatedAt       time.Time
}

func (User) TableName() string { return "users" }

type Chat struct {
	ID        uuid.UUID `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
	UserID    uuid.UUID `gorm:"type:uuid;not null;index"`
	User      User      `gorm:"constraint:OnDelete:CASCADE"`
	PostType  PostType  `gorm:"type:post_type_enum;not null"`
	Title     *string   `gorm:"size:255"`
	CreatedAt time.Time
	UpdatedAt time.Time
	Contents  []ChatContent      `gorm:"foreignKey:ChatID"`
	Resume    *ChatContentResume `gorm:"foreignKey:ChatID"`
}

func (Chat) TableName() string { return "chats" }

type ChatContent struct {
	ID        uuid.UUID       `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
	ChatID    uuid.UUID       `gorm:"type:uuid;not null;index"`
	Chat      Chat            `gorm:"constraint:OnDelete:CASCADE"`
	Role      ChatContentRole `gorm:"type:chat_content_role_enum;not null"`
	Content   string          `gorm:"type:text;not null"`
	CreatedAt time.Time
	UpdatedAt time.Time
	Images    []ChatContentImage `gorm:"foreignKey:ChatContentID"`
}

func (ChatContent) TableName() string { return "chat_content" }

type ChatContentImage struct {
	ID            uuid.UUID   `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
	ChatContentID uuid.UUID   `gorm:"type:uuid;not null;index"`
	ChatContent   ChatContent `gorm:"constraint:OnDelete:CASCADE"`
	S3Key         string      `gorm:"column:s3_key;size:512;not null"`
	URL           string      `gorm:"size:1024;not null"`
	SlideNumber   int         `gorm:"column:slide_number;not null"`
	CreatedAt     time.Time
	UpdatedAt     time.Time
}

func (ChatContentImage) TableName() string { return "chat_content_image" }

type ChatContentResume struct {
	ID            uuid.UUID  `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
	ChatID        uuid.UUID  `gorm:"type:uuid;not null;uniqueIndex"`
	Chat          Chat       `gorm:"constraint:OnDelete:CASCADE"`
	Summary       *string    `gorm:"type:text"`
	LastContentAt *time.Time `gorm:"column:last_content_at"`
	SummarizedAt  *time.Time `gorm:"column:summarized_at"`
	CreatedAt     time.Time
	UpdatedAt     time.Time
}

func (ChatContentResume) TableName() string { return "chat_content_resume" }

// JobStatus is stored as PostgreSQL enum job_status_enum.
type JobStatus string

const (
	JobStatusPending    JobStatus = "pending"
	JobStatusProcessing JobStatus = "processing"
	JobStatusDone       JobStatus = "done"
	JobStatusFailed     JobStatus = "failed"
)

// Job tracks async worker runs for a chat message.
type Job struct {
	ID        uuid.UUID `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
	ChatID    uuid.UUID `gorm:"type:uuid;not null;index"`
	UserID    uuid.UUID `gorm:"type:uuid;not null;index"`
	Status    JobStatus `gorm:"type:job_status_enum;not null;default:pending"`
	ErrorMsg  *string   `gorm:"type:text"`
	CreatedAt time.Time
	UpdatedAt time.Time
}

func (Job) TableName() string { return "jobs" }

type UserProfile struct {
	ID        uuid.UUID `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
	UserID    uuid.UUID `gorm:"type:uuid;not null;uniqueIndex"`
	User      User      `gorm:"constraint:OnDelete:CASCADE"`
	AuditText string    `gorm:"column:audit_text;not null;default:''"`
	BrandText string    `gorm:"column:brand_text;not null;default:''"`
	CreatedAt time.Time
	UpdatedAt time.Time
}

func (UserProfile) TableName() string { return "user_profiles" }

// UserProfileReference is an optional design reference image (S3) for a user profile.
type UserProfileReference struct {
	ID        uuid.UUID `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
	UserID    uuid.UUID `gorm:"type:uuid;not null;index"`
	User      User      `gorm:"constraint:OnDelete:CASCADE"`
	S3Key     string    `gorm:"column:s3_key;size:512;not null"`
	SortOrder int       `gorm:"column:sort_order;not null;default:0"`
	CreatedAt time.Time
}

func (UserProfileReference) TableName() string { return "user_profile_references" }

// RefreshToken persists issued refresh token JTIs for revocation and rotation.
type RefreshToken struct {
	JTI       uuid.UUID  `gorm:"type:uuid;primaryKey"`
	UserID    uuid.UUID  `gorm:"type:uuid;not null;index"`
	User      User       `gorm:"constraint:OnDelete:CASCADE"`
	ExpiresAt time.Time  `gorm:"not null"`
	RevokedAt *time.Time `gorm:"column:revoked_at"`
	CreatedAt time.Time
}

func (RefreshToken) TableName() string { return "refresh_tokens" }
