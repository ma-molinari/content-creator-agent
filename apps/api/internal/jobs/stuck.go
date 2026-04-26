package jobs

import (
	"context"
	"time"
)

// RunStuckJobCleanup marks processing jobs older than maxAge as failed.
func RunStuckJobCleanup(ctx context.Context, repo *Repository, maxAge time.Duration) (int64, error) {
	if maxAge <= 0 {
		return 0, nil
	}
	cutoff := time.Now().UTC().Add(-maxAge)
	return repo.FailStuckProcessingJobs(ctx, cutoff, StuckJobErrorMsg)
}
