package auth

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"net/mail"
	"strings"
	"time"

	"content-creator-agent/internal/db"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"
)

const (
	bcryptCost = 12
	// AccessTokenTTL is the signed JWT duration returned on login and refresh.
	AccessTokenTTL = 4 * time.Hour
	// RefreshTokenTTL is the signed refresh JWT and Set-Cookie MaxAge.
	RefreshTokenTTL = 7 * 24 * time.Hour
	accessTokenTTL  = AccessTokenTTL
	refreshTokenTTL = RefreshTokenTTL

	loginMaxAttempts   = 5
	loginLockoutWindow = 15 * time.Minute
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
	if _, err := mail.ParseAddress(email); email == "" || err != nil {
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
		ID:              uuid.New(),
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

	// Check lockout before bcrypt to avoid timing oracle when account is locked.
	since := time.Now().UTC().Add(-loginLockoutWindow)
	count, err := s.repo.CountRecentLoginAttempts(ctx, u.ID, since)
	if err != nil {
		return nil, err
	}
	if count >= loginMaxAttempts {
		return nil, errStatus(http.StatusTooManyRequests, "too many failed login attempts, try again later")
	}

	if err := bcrypt.CompareHashAndPassword([]byte(u.PasswordHash), []byte(password)); err != nil {
		_ = s.repo.RecordLoginAttempt(ctx, u.ID)
		return nil, errStatus(http.StatusUnauthorized, "invalid credentials")
	}

	_ = s.repo.ClearLoginAttempts(ctx, u.ID)
	access, refresh, err := s.issueTokens(ctx, u.ID)
	if err != nil {
		return nil, err
	}
	return &LoginResult{AccessToken: access, RefreshToken: refresh}, nil
}

// signTokens signs both JWTs and returns the model to persist — no I/O.
func (s *Service) signTokens(userID uuid.UUID) (access string, refresh string, rt *db.RefreshToken, err error) {
	now := time.Now()
	accessClaims := jwt.RegisteredClaims{
		Subject:   userID.String(),
		IssuedAt:  jwt.NewNumericDate(now),
		ExpiresAt: jwt.NewNumericDate(now.Add(accessTokenTTL)),
	}
	at := jwt.NewWithClaims(jwt.SigningMethodHS256, accessClaims)
	access, err = at.SignedString(s.jwtSecret)
	if err != nil {
		return "", "", nil, err
	}
	jti := uuid.New()
	expiresAt := now.Add(refreshTokenTTL)
	refreshClaims := jwt.RegisteredClaims{
		Subject:   userID.String(),
		ID:        jti.String(),
		IssuedAt:  jwt.NewNumericDate(now),
		ExpiresAt: jwt.NewNumericDate(expiresAt),
	}
	rtJWT := jwt.NewWithClaims(jwt.SigningMethodHS256, refreshClaims)
	refresh, err = rtJWT.SignedString(s.jwtRefreshSecret)
	if err != nil {
		return "", "", nil, err
	}
	return access, refresh, &db.RefreshToken{JTI: jti, UserID: userID, ExpiresAt: expiresAt}, nil
}

func (s *Service) issueTokens(ctx context.Context, userID uuid.UUID) (access string, refresh string, err error) {
	access, refresh, rt, err := s.signTokens(userID)
	if err != nil {
		return "", "", err
	}
	if err = s.repo.CreateRefreshToken(ctx, rt); err != nil {
		return "", "", err
	}
	return access, refresh, nil
}

type RefreshResult struct {
	AccessToken  string
	RefreshToken string
}

func (s *Service) Refresh(ctx context.Context, refreshToken string) (*RefreshResult, error) {
	if refreshToken == "" {
		return nil, errStatus(http.StatusUnauthorized, "missing refresh token")
	}
	parser := jwt.NewParser(jwt.WithValidMethods([]string{jwt.SigningMethodHS256.Alg()}))
	tok, err := parser.ParseWithClaims(refreshToken, &jwt.RegisteredClaims{}, func(t *jwt.Token) (interface{}, error) {
		if t.Method != jwt.SigningMethodHS256 {
			return nil, fmt.Errorf("unexpected signing method")
		}
		return s.jwtRefreshSecret, nil
	})
	if err != nil || !tok.Valid {
		return nil, errStatus(http.StatusUnauthorized, "invalid or expired refresh token")
	}
	claims, ok := tok.Claims.(*jwt.RegisteredClaims)
	if !ok || claims.Subject == "" || claims.ID == "" {
		return nil, errStatus(http.StatusUnauthorized, "invalid refresh token")
	}
	userID, err := uuid.Parse(claims.Subject)
	if err != nil {
		return nil, errStatus(http.StatusUnauthorized, "invalid refresh token")
	}
	jti, err := uuid.Parse(claims.ID)
	if err != nil {
		return nil, errStatus(http.StatusUnauthorized, "invalid refresh token")
	}
	record, err := s.repo.FindRefreshToken(ctx, jti)
	if err != nil {
		return nil, err
	}
	if record == nil || record.RevokedAt != nil {
		return nil, errStatus(http.StatusUnauthorized, "refresh token revoked")
	}
	u, err := s.repo.FindByID(ctx, userID)
	if err != nil {
		return nil, err
	}
	if u == nil {
		return nil, errStatus(http.StatusUnauthorized, "invalid refresh token")
	}
	access, newRefresh, newRT, err := s.signTokens(userID)
	if err != nil {
		return nil, err
	}
	if err := s.repo.RevokeAndCreateRefreshToken(ctx, jti, newRT); err != nil {
		return nil, err
	}
	return &RefreshResult{AccessToken: access, RefreshToken: newRefresh}, nil
}

// Logout revokes the JTI embedded in the refresh token, if valid.
func (s *Service) Logout(ctx context.Context, refreshToken string) {
	if refreshToken == "" {
		return
	}
	parser := jwt.NewParser(jwt.WithValidMethods([]string{jwt.SigningMethodHS256.Alg()}))
	tok, err := parser.ParseWithClaims(refreshToken, &jwt.RegisteredClaims{}, func(t *jwt.Token) (interface{}, error) {
		return s.jwtRefreshSecret, nil
	})
	if err != nil || !tok.Valid {
		return
	}
	claims, ok := tok.Claims.(*jwt.RegisteredClaims)
	if !ok || claims.ID == "" {
		return
	}
	jti, err := uuid.Parse(claims.ID)
	if err != nil {
		return
	}
	if err := s.repo.RevokeRefreshToken(ctx, jti); err != nil {
		log.Printf("[auth] logout: revoke jti=%s err=%v", jti, err)
	}
}

func (s *Service) RecoverPassword(ctx context.Context, email, securityKey, newPassword string) error {
	email = strings.TrimSpace(strings.ToLower(email))
	if len(newPassword) < 8 {
		return errStatus(http.StatusBadRequest, "password must be at least 8 characters")
	}
	u, err := s.repo.FindByEmail(ctx, email)
	if err != nil {
		return err
	}
	if u == nil {
		// Same outcome as wrong security key: do not reveal whether the email exists.
		return nil
	}
	if err := bcrypt.CompareHashAndPassword([]byte(u.SecurityKeyHash), []byte(securityKey)); err != nil {
		return nil
	}
	passHash, err := bcrypt.GenerateFromPassword([]byte(newPassword), bcryptCost)
	if err != nil {
		return err
	}
	return s.repo.UpdatePasswordHash(ctx, u.ID, string(passHash))
}

// CookieSecure returns whether Set-Cookie should use the Secure flag.
func (s *Service) CookieSecure() bool { return s.cookieSecure }
