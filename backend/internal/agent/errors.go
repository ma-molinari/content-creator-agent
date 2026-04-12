package agent

import "errors"

// ErrSetupRequired is returned when AUDIT.md or BRAND.md is missing for the user.
var ErrSetupRequired = errors.New("agent: profile setup required (AUDIT.md and BRAND.md)")

// ErrLLMNotConfigured is returned when the OpenAI client was not wired.
var ErrLLMNotConfigured = errors.New("agent: llm not configured")

// ErrEmptyPrompt is returned when user input is empty after sanitization.
var ErrEmptyPrompt = errors.New("agent: empty prompt after sanitization")
