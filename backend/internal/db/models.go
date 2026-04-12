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
	ChatContentRoleUser       ChatContentRole = "user"
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
	Contents  []ChatContent `gorm:"foreignKey:ChatID"`
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
	ID            uuid.UUID `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
	ChatContentID uuid.UUID `gorm:"type:uuid;not null;index"`
	ChatContent   ChatContent `gorm:"constraint:OnDelete:CASCADE"`
	S3Key         string    `gorm:"column:s3_key;size:512;not null"`
	URL           string    `gorm:"size:1024;not null"`
	SlideNumber   int       `gorm:"column:slide_number;not null"`
	CreatedAt     time.Time
	UpdatedAt     time.Time
}

func (ChatContentImage) TableName() string { return "chat_content_image" }

type ChatContentResume struct {
	ID             uuid.UUID  `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
	ChatID         uuid.UUID  `gorm:"type:uuid;not null;uniqueIndex"`
	Chat           Chat       `gorm:"constraint:OnDelete:CASCADE"`
	Summary        *string    `gorm:"type:text"`
	LastContentAt  *time.Time `gorm:"column:last_content_at"`
	SummarizedAt   *time.Time `gorm:"column:summarized_at"`
	CreatedAt      time.Time
	UpdatedAt      time.Time
}

func (ChatContentResume) TableName() string { return "chat_content_resume" }
