package auth

import (
	"context"
	"net/http"
	"testing"

	"github.com/stretchr/testify/require"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

const testJWTAccess = "integration-test-jwt-access-secret-min-32-chars"
const testJWTRefresh = "integration-test-jwt-refresh-secret-min-32-chars"

func testAuthDB(t *testing.T) *gorm.DB {
	t.Helper()
	gdb, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	require.NoError(t, err)
	require.NoError(t, gdb.Exec(`CREATE TABLE users (
		id TEXT PRIMARY KEY,
		email TEXT NOT NULL UNIQUE,
		password_hash TEXT NOT NULL,
		security_key_hash TEXT NOT NULL,
		role TEXT NOT NULL,
		created_at DATETIME,
		updated_at DATETIME
	)`).Error)
	return gdb
}

func TestRegister_ShortPassword(t *testing.T) {
	repo := NewRepository(testAuthDB(t))
	svc := NewService(repo, testJWTAccess, testJWTRefresh, false)
	_, err := svc.Register(context.Background(), "a@b.com", "short")
	require.Error(t, err)
	var se *ServiceError
	require.ErrorAs(t, err, &se)
	require.Equal(t, http.StatusBadRequest, se.HTTPStatus)
}

func TestRegister_InvalidEmail(t *testing.T) {
	repo := NewRepository(testAuthDB(t))
	svc := NewService(repo, testJWTAccess, testJWTRefresh, false)
	_, err := svc.Register(context.Background(), "not-an-email", "password123")
	require.Error(t, err)
	var se *ServiceError
	require.ErrorAs(t, err, &se)
	require.Equal(t, http.StatusBadRequest, se.HTTPStatus)
}

func TestRegister_DuplicateEmail(t *testing.T) {
	gdb := testAuthDB(t)
	repo := NewRepository(gdb)
	svc := NewService(repo, testJWTAccess, testJWTRefresh, false)
	ctx := context.Background()
	_, err := svc.Register(ctx, "dup@example.com", "password123")
	require.NoError(t, err)
	_, err = svc.Register(ctx, "dup@example.com", "password456")
	require.Error(t, err)
	var se *ServiceError
	require.ErrorAs(t, err, &se)
	require.Equal(t, http.StatusConflict, se.HTTPStatus)
}

func TestRegister_Success(t *testing.T) {
	repo := NewRepository(testAuthDB(t))
	svc := NewService(repo, testJWTAccess, testJWTRefresh, false)
	res, err := svc.Register(context.Background(), "new@example.com", "password123")
	require.NoError(t, err)
	require.NotNil(t, res)
	require.NotEmpty(t, res.SecurityKey)
}

func TestLogin_WrongPassword(t *testing.T) {
	gdb := testAuthDB(t)
	repo := NewRepository(gdb)
	svc := NewService(repo, testJWTAccess, testJWTRefresh, false)
	_, err := svc.Register(context.Background(), "u@example.com", "password123")
	require.NoError(t, err)
	_, err = svc.Login(context.Background(), "u@example.com", "wrong-pass")
	require.Error(t, err)
	var se *ServiceError
	require.ErrorAs(t, err, &se)
	require.Equal(t, http.StatusUnauthorized, se.HTTPStatus)
}

func TestLogin_Valid(t *testing.T) {
	repo := NewRepository(testAuthDB(t))
	svc := NewService(repo, testJWTAccess, testJWTRefresh, false)
	_, err := svc.Register(context.Background(), "ok@example.com", "password123")
	require.NoError(t, err)
	res, err := svc.Login(context.Background(), "ok@example.com", "password123")
	require.NoError(t, err)
	require.NotEmpty(t, res.AccessToken)
	require.NotEmpty(t, res.RefreshToken)
}

func TestRefresh_EmptyToken(t *testing.T) {
	repo := NewRepository(testAuthDB(t))
	svc := NewService(repo, testJWTAccess, testJWTRefresh, false)
	_, err := svc.Refresh(context.Background(), "")
	require.Error(t, err)
	var se *ServiceError
	require.ErrorAs(t, err, &se)
	require.Equal(t, http.StatusUnauthorized, se.HTTPStatus)
}

func TestRefresh_InvalidToken(t *testing.T) {
	repo := NewRepository(testAuthDB(t))
	svc := NewService(repo, testJWTAccess, testJWTRefresh, false)
	_, err := svc.Refresh(context.Background(), "not-a-valid-jwt")
	require.Error(t, err)
	var se *ServiceError
	require.ErrorAs(t, err, &se)
	require.Equal(t, http.StatusUnauthorized, se.HTTPStatus)
}

func TestRecoverPassword_WrongKey_NoLeak(t *testing.T) {
	gdb := testAuthDB(t)
	repo := NewRepository(gdb)
	svc := NewService(repo, testJWTAccess, testJWTRefresh, false)
	_, err := svc.Register(context.Background(), "rec@example.com", "password123")
	require.NoError(t, err)
	err = svc.RecoverPassword(context.Background(), "rec@example.com", "wrong-security-key", "newpassword12")
	require.NoError(t, err)
	_, err = svc.Login(context.Background(), "rec@example.com", "password123")
	require.NoError(t, err)
}

func TestRecoverPassword_UnknownEmail_SameAsWrongKey(t *testing.T) {
	repo := NewRepository(testAuthDB(t))
	svc := NewService(repo, testJWTAccess, testJWTRefresh, false)
	err := svc.RecoverPassword(context.Background(), "nobody@example.com", "any-key", "newpassword12")
	require.NoError(t, err)
}

func TestRecoverPassword_Valid(t *testing.T) {
	gdb := testAuthDB(t)
	repo := NewRepository(gdb)
	svc := NewService(repo, testJWTAccess, testJWTRefresh, false)
	res, err := svc.Register(context.Background(), "rec2@example.com", "password123")
	require.NoError(t, err)
	err = svc.RecoverPassword(context.Background(), "rec2@example.com", res.SecurityKey, "newpassword99")
	require.NoError(t, err)
	_, err = svc.Login(context.Background(), "rec2@example.com", "newpassword99")
	require.NoError(t, err)
}
