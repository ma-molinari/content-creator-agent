# content-creator-agent

Monorepo layout: `apps/api` (Go API), `apps/worker` (Python LangGraph worker; prompts in `apps/worker/prompts/`), `apps/web` (frontend placeholder).

Skills e rules de prompts vivem em `.cursor/`; o worker Python deve carregar a partir desse diretório (ou de caminhos configuráveis no próprio worker).
