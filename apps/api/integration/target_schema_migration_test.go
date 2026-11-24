//go:build integration

package integration

import (
	"context"
	"os"
	"testing"

	"content-creator-agent/internal/db"
	"github.com/stretchr/testify/require"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

func TestTargetSchemaMigrationPreservesOldJobs(t *testing.T) {
	dsn := os.Getenv("INTEGRATION_DATABASE_URL")
	if dsn == "" {
		t.Skip("INTEGRATION_DATABASE_URL not set")
	}
	conn, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	require.NoError(t, err)
	tx := conn.WithContext(context.Background()).Begin()
	require.NoError(t, tx.Error)
	defer tx.Rollback()
	require.NoError(t, tx.Exec(`CREATE TEMP TABLE jobs (id integer PRIMARY KEY, post_format text NOT NULL) ON COMMIT DROP`).Error)
	require.NoError(t, tx.Exec(`CREATE TEMP TABLE post_versions (schema_version integer NOT NULL) ON COMMIT DROP`).Error)
	require.NoError(t, tx.Exec(`INSERT INTO jobs VALUES (1, 'structured_v1'), (2, 'legacy_html')`).Error)
	up, err := os.ReadFile("../internal/db/migrations/019_add_job_target_schema.up.sql")
	require.NoError(t, err)
	require.NoError(t, tx.Exec(string(up)).Error)
	var old struct{ TargetSchemaVersion *int }
	require.NoError(t, tx.Raw(`SELECT target_schema_version FROM jobs WHERE id = 1`).Scan(&old).Error)
	require.Nil(t, old.TargetSchemaVersion)
	require.Equal(t, 1, (db.Job{TargetSchemaVersion: old.TargetSchemaVersion}).StructuredTargetSchema())
	require.NoError(t, tx.Exec(`INSERT INTO jobs (id, post_format, target_schema_version) VALUES (3, 'structured_v1', 1), (4, 'structured_v1', 2), (5, 'structured_v1', NULL)`).Error)
	require.NoError(t, tx.Exec(`SAVEPOINT invalid_target`).Error)
	require.Error(t, tx.Exec(`INSERT INTO jobs (id, post_format, target_schema_version) VALUES (6, 'structured_v1', 3)`).Error)
	require.NoError(t, tx.Exec(`ROLLBACK TO SAVEPOINT invalid_target`).Error)
	down, err := os.ReadFile("../internal/db/migrations/019_add_job_target_schema.down.sql")
	require.NoError(t, err)
	require.NoError(t, tx.Exec(`SAVEPOINT safe_rollback`).Error)
	require.Error(t, tx.Exec(string(down)).Error)
	require.NoError(t, tx.Exec(`ROLLBACK TO SAVEPOINT safe_rollback`).Error)
	require.NoError(t, tx.Exec(`DELETE FROM jobs WHERE target_schema_version = 2`).Error)
	require.NoError(t, tx.Exec(`INSERT INTO post_versions VALUES (2)`).Error)
	require.NoError(t, tx.Exec(`SAVEPOINT version_rollback`).Error)
	require.Error(t, tx.Exec(string(down)).Error)
	require.NoError(t, tx.Exec(`ROLLBACK TO SAVEPOINT version_rollback`).Error)
	require.NoError(t, tx.Exec(`DELETE FROM post_versions`).Error)
	require.NoError(t, tx.Exec(string(down)).Error)
}

func TestV3TargetMigrationBlocksUnsafeRollback(t *testing.T) {
	dsn := os.Getenv("INTEGRATION_DATABASE_URL")
	if dsn == "" {
		t.Skip("INTEGRATION_DATABASE_URL not set")
	}
	conn, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	require.NoError(t, err)
	tx := conn.WithContext(context.Background()).Begin()
	require.NoError(t, tx.Error)
	defer tx.Rollback()
	require.NoError(t, tx.Exec(`CREATE TEMP TABLE jobs (target_schema_version integer, CONSTRAINT jobs_target_schema_version_check CHECK (target_schema_version IS NULL OR target_schema_version IN (1,2))) ON COMMIT DROP`).Error)
	require.NoError(t, tx.Exec(`CREATE TEMP TABLE post_versions (schema_version integer NOT NULL) ON COMMIT DROP`).Error)
	up, err := os.ReadFile("../internal/db/migrations/020_add_job_schema_v3.up.sql")
	require.NoError(t, err)
	require.NoError(t, tx.Exec(string(up)).Error)
	require.NoError(t, tx.Exec(`INSERT INTO jobs VALUES (1),(2),(3)`).Error)
	down, err := os.ReadFile("../internal/db/migrations/020_add_job_schema_v3.down.sql")
	require.NoError(t, err)
	require.NoError(t, tx.Exec(`SAVEPOINT has_job`).Error)
	require.Error(t, tx.Exec(string(down)).Error)
	require.NoError(t, tx.Exec(`ROLLBACK TO SAVEPOINT has_job`).Error)
	require.NoError(t, tx.Exec(`DELETE FROM jobs WHERE target_schema_version = 3`).Error)
	require.NoError(t, tx.Exec(`INSERT INTO post_versions VALUES (3)`).Error)
	require.NoError(t, tx.Exec(`SAVEPOINT has_version`).Error)
	require.Error(t, tx.Exec(string(down)).Error)
	require.NoError(t, tx.Exec(`ROLLBACK TO SAVEPOINT has_version`).Error)
	require.NoError(t, tx.Exec(`DELETE FROM post_versions`).Error)
	require.NoError(t, tx.Exec(string(down)).Error)
}
