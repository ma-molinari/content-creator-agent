package cron

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestSafelyRun_RunsNormally(t *testing.T) {
	t.Parallel()
	var n int
	SafelyRun("test_ok", func() { n++ })
	require.Equal(t, 1, n)
}

func TestSafelyRun_RecoversPanic(t *testing.T) {
	t.Parallel()
	require.NotPanics(t, func() {
		SafelyRun("test_panic", func() {
			panic("intentional panic for test")
		})
	})
}
