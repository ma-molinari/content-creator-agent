package cron

import (
	"log"
	"runtime/debug"
)

// SafelyRun executes fn wrapped in recover; panics are logged with job name and stack.
func SafelyRun(name string, fn func()) {
	defer func() {
		if r := recover(); r != nil {
			log.Printf("[cron] job=%s panic=%v stack:\n%s", name, r, debug.Stack())
		}
	}()
	fn()
}
