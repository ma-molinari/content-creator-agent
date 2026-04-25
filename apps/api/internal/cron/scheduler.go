package cron

import (
	"time"

	robfig "github.com/robfig/cron/v3"
)

// Scheduler wraps robfig/cron with UTC location.
type Scheduler struct {
	c *robfig.Cron
}

// New returns a scheduler using UTC for all expressions.
func New() *Scheduler {
	return &Scheduler{c: robfig.New(robfig.WithLocation(time.UTC))}
}

// Register adds a job with a standard cron expression (e.g. "0 2 * * *").
func (s *Scheduler) Register(expr string, fn func()) error {
	_, err := s.c.AddFunc(expr, fn)
	return err
}

// Start begins executing registered jobs.
func (s *Scheduler) Start() { s.c.Start() }

// Stop stops the scheduler and waits for running jobs to finish.
func (s *Scheduler) Stop() { s.c.Stop() }
