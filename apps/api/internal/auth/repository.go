package auth

import (
	"context"
	"errors"
	"time"

	"content-creator-agent/internal/db"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type Repository struct {
	gdb *gorm.DB
}

func NewRepository(gdb *gorm.DB) *Repository {
	return &Repository{gdb: gdb}
}

func (r *Repository) CreateUser(ctx context.Context, u *db.User) error {
	return r.gdb.WithContext(ctx).Create(u).Error
}

func (r *Repository) FindByEmail(ctx context.Context, email string) (*db.User, error) {
	var u db.User
	err := r.gdb.WithContext(ctx).Where("email = ?", email).First(&u).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, err
	}
	return &u, nil
}

func (r *Repository) FindByID(ctx context.Context, id uuid.UUID) (*db.User, error) {
	var u db.User
	err := r.gdb.WithContext(ctx).Where("id = ?", id).First(&u).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, err
	}
	return &u, nil
}

func (r *Repository) UpdatePasswordHash(ctx context.Context, userID uuid.UUID, passwordHash string) error {
	res := r.gdb.WithContext(ctx).Model(&db.User{}).Where("id = ?", userID).Update("password_hash", passwordHash)
	if res.Error != nil {
		return res.Error
	}
	if res.RowsAffected == 0 {
		return gorm.ErrRecordNotFound
	}
	return nil
}

func (r *Repository) CreateRefreshToken(ctx context.Context, rt *db.RefreshToken) error {
	return r.gdb.WithContext(ctx).Create(rt).Error
}

func (r *Repository) FindRefreshToken(ctx context.Context, jti uuid.UUID) (*db.RefreshToken, error) {
	var rt db.RefreshToken
	err := r.gdb.WithContext(ctx).Where("jti = ?", jti).First(&rt).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, err
	}
	return &rt, nil
}

func (r *Repository) RevokeRefreshToken(ctx context.Context, jti uuid.UUID) error {
	now := time.Now()
	res := r.gdb.WithContext(ctx).Model(&db.RefreshToken{}).
		Where("jti = ? AND revoked_at IS NULL", jti).
		Update("revoked_at", now)
	return res.Error
}
