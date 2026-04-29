package cron

import (
	"log"
	"runtime/debug"
)

// SafelyRun invokes fn and recovers panics so the robfig/cron worker goroutine is not aborted.
func SafelyRun(name string, fn func()) {
	defer func() {
		if r := recover(); r != nil {
			log.Printf("[cron:%s] panic recovered: %v\n%s", name, r, debug.Stack())
		}
	}()
	fn()
}
