package cron

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestSafelyRun_RunsNormal(t *testing.T) {
	t.Parallel()
	var ran bool
	SafelyRun("test-job", func() {
		ran = true
	})
	require.True(t, ran)
}

func TestSafelyRun_RecoversPanic(t *testing.T) {
	t.Parallel()
	require.NotPanics(t, func() {
		SafelyRun("panic-job", func() {
			panic("intentional")
		})
	})
}
