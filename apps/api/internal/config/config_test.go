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
