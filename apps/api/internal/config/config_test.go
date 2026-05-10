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
