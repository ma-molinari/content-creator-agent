package auth

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"

	"content-creator-agent/internal/db"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"
)

const (
	bcryptCost      = 12
	accessTokenTTL  = 15 * time.Minute
	refreshTokenTTL = 7 * 24 * time.Hour
)

// ServiceError carries an HTTP status for handlers.
type ServiceError struct {
	HTTPStatus int
	Message    string
}

func (e *ServiceError) Error() string { return e.Message }

func errStatus(status int, msg string) error {
	return &ServiceError{HTTPStatus: status, Message: msg}
}

type Service struct {
	repo             *Repository
	jwtSecret        []byte
	jwtRefreshSecret []byte
	cookieSecure     bool
}

func NewService(repo *Repository, jwtSecret, jwtRefreshSecret string, cookieSecure bool) *Service {
	return &Service{
		repo:             repo,
		jwtSecret:        []byte(jwtSecret),
		jwtRefreshSecret: []byte(jwtRefreshSecret),
		cookieSecure:     cookieSecure,
	}
}

type RegisterResult struct {
	SecurityKey string
}

func (s *Service) Register(ctx context.Context, email, password string) (*RegisterResult, error) {
	email = strings.TrimSpace(strings.ToLower(email))
	if len(password) < 8 {
		return nil, errStatus(http.StatusBadRequest, "password must be at least 8 characters")
	}
	if email == "" || !strings.Contains(email, "@") {
		return nil, errStatus(http.StatusBadRequest, "invalid email")
	}
	existing, err := s.repo.FindByEmail(ctx, email)
	if err != nil {
		return nil, err
	}
	if existing != nil {
		return nil, errStatus(http.StatusConflict, "email already registered")
	}
	secKey := uuid.New().String()
	secHash, err := bcrypt.GenerateFromPassword([]byte(secKey), bcryptCost)
	if err != nil {
		return nil, err
	}
	passHash, err := bcrypt.GenerateFromPassword([]byte(password), bcryptCost)
	if err != nil {
		return nil, err
	}
	u := &db.User{
		Email:           email,
		PasswordHash:    string(passHash),
		SecurityKeyHash: string(secHash),
		Role:            db.RoleUser,
	}
	if err := s.repo.CreateUser(ctx, u); err != nil {
		return nil, err
	}
	return &RegisterResult{SecurityKey: secKey}, nil
}

type LoginResult struct {
	AccessToken  string
	RefreshToken string
}

func (s *Service) Login(ctx context.Context, email, password string) (*LoginResult, error) {
	email = strings.TrimSpace(strings.ToLower(email))
	u, err := s.repo.FindByEmail(ctx, email)
	if err != nil {
		return nil, err
	}
	if u == nil {
		return nil, errStatus(http.StatusUnauthorized, "invalid credentials")
	}
	if err := bcrypt.CompareHashAndPassword([]byte(u.PasswordHash), []byte(password)); err != nil {
		return nil, errStatus(http.StatusUnauthorized, "invalid credentials")
	}
	access, refresh, err := s.issueTokens(u.ID)
	if err != nil {
		return nil, err
	}
	return &LoginResult{AccessToken: access, RefreshToken: refresh}, nil
}

func (s *Service) issueTokens(userID uuid.UUID) (access string, refresh string, err error) {
	now := time.Now()
	accessClaims := jwt.RegisteredClaims{
		Subject:   userID.String(),
		IssuedAt:  jwt.NewNumericDate(now),
		ExpiresAt: jwt.NewNumericDate(now.Add(accessTokenTTL)),
	}
	at := jwt.NewWithClaims(jwt.SigningMethodHS256, accessClaims)
	access, err = at.SignedString(s.jwtSecret)
	if err != nil {
		return "", "", err
	}
	refreshClaims := jwt.RegisteredClaims{
		Subject:   userID.String(),
		IssuedAt:  jwt.NewNumericDate(now),
		ExpiresAt: jwt.NewNumericDate(now.Add(refreshTokenTTL)),
	}
	rt := jwt.NewWithClaims(jwt.SigningMethodHS256, refreshClaims)
	refresh, err = rt.SignedString(s.jwtRefreshSecret)
	if err != nil {
		return "", "", err
	}
	return access, refresh, nil
}
