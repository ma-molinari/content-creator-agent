package config

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestStuckJobCronDefault(t *testing.T) {
	t.Setenv("STUCK_JOB_CRON", "")
	cfg := Load()
	require.Equal(t, "*/10 * * * *", cfg.StuckJobCron)
}

func TestArtifactReconciliationDefaultsAndBounds(t *testing.T) {
	t.Setenv("ARTIFACT_RECONCILE_ENABLED", "")
	t.Setenv("ARTIFACT_RECONCILE_CRON", "")
	t.Setenv("ARTIFACT_RECONCILE_GRACE_HOURS", "1")
	cfg := Load()
	require.False(t, cfg.ArtifactReconcileEnabled)
	require.Equal(t, "0 4 * * *", cfg.ArtifactReconcileCron)
	require.Equal(t, 24, cfg.ArtifactReconcileGraceHours)
	t.Setenv("ARTIFACT_RECONCILE_ENABLED", "true")
	t.Setenv("ARTIFACT_RECONCILE_GRACE_HOURS", "48")
	cfg = Load()
	require.True(t, cfg.ArtifactReconcileEnabled)
	require.Equal(t, 48, cfg.ArtifactReconcileGraceHours)
}

func TestStructuredPostsDisabledByDefault(t *testing.T) {
	t.Setenv("STRUCTURED_POSTS_ENABLED", "")
	require.False(t, Load().StructuredPostsEnabled)
	t.Setenv("STRUCTURED_POSTS_ENABLED", "true")
	require.True(t, Load().StructuredPostsEnabled)
}

func TestVisualV2FlagsDefaultOff(t *testing.T) {
	t.Setenv("STRUCTURED_VISUAL_V2_ENABLED", "")
	t.Setenv("STRUCTURED_VISUAL_V2_MUTATIONS_DISABLED", "")
	require.False(t, Load().StructuredVisualV2Enabled)
	require.False(t, Load().StructuredVisualV2MutationsDisabled)
	t.Setenv("STRUCTURED_VISUAL_V2_ENABLED", "true")
	t.Setenv("STRUCTURED_VISUAL_V2_MUTATIONS_DISABLED", "true")
	require.True(t, Load().StructuredVisualV2Enabled)
	require.True(t, Load().StructuredVisualV2MutationsDisabled)
}

func TestStructuredWorkerURLs(t *testing.T) {
	t.Setenv("STRUCTURED_WORKER_URLS", " http://worker-a:8000, ,http://worker-b:8000 ")
	require.Equal(t, []string{"http://worker-a:8000", "http://worker-b:8000"}, Load().StructuredWorkerURLs)
}

func TestS3LocalEndpointSettings(t *testing.T) {
	t.Setenv("AWS_S3_FORCE_PATH_STYLE", "")
	t.Setenv("AWS_S3_PUBLIC_ENDPOINT", "")
	require.False(t, Load().S3ForcePathStyle)
	require.Empty(t, Load().S3PublicEndpoint)
	t.Setenv("AWS_S3_FORCE_PATH_STYLE", "true")
	t.Setenv("AWS_S3_PUBLIC_ENDPOINT", " http://localhost:4566 ")
	cfg := Load()
	require.True(t, cfg.S3ForcePathStyle)
	require.Equal(t, "http://localhost:4566", cfg.S3PublicEndpoint)
}
