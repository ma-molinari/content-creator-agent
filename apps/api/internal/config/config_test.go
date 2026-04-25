package config

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestSummarizeCronDefault(t *testing.T) {
	t.Setenv("SUMMARIZE_CRON", "")
	cfg := Load()
	require.Equal(t, "0 2 * * *", cfg.SummarizeCron)
}
