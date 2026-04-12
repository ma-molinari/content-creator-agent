# content-creator-agent

## Backend prompts

Depois de alterar rules/skills em `.cursor/` usadas pelo fluxo de carrossel da API, na pasta `backend/` execute `make prompts-sync` para atualizar `internal/agent/promptdata/` (cópias embebidas com `go:embed`).
