# Estado da Sessão — Content Creator Agent

## Última atualização

2026-04-13

## Feature em foco

| Item | Valor |
|------|--------|
| Spec | `.specs/features/content-creator-agent/spec.md` |
| Design | `.specs/features/content-creator-agent/design.md` |
| Tasks | `.specs/features/content-creator-agent/tasks.md` |
| TDD | `docs/TDD.md` |
| Arquitetura | `docs/architecture-go-api-langgraph.md` |

## Status vs plano de tasks

| Fase | Escopo (tasks.md) | Estado |
|------|-------------------|--------|
| **Fase 1 — Go API limpa** | T1–T14 | **Concluída (código)** — `apps/api/`: Echo, auth (JWT + refresh httpOnly), rate limit, CRUD chats (limite 5 + eviction), S3, arquivos/zip, jobs async (`POST /chats/:id/messages` → 202 + `jobId`), callback interno, polling de status, `GET /setup/status`. **Ressalvas vs tasks.md:** (1) **T9** — `Upload` tem backoff 3×; **`DeleteMany` não** (apenas batch DeleteObjects). (2) Nomes de env: código usa `AWS_REGION` / `AWS_S3_BUCKET` / etc.; o `tasks.md` menciona `S3_*` no texto — equivalente, só nomenclatura. |
| **Fase 2 — Worker Python LangGraph** | TP1–TP11 | **Concluída (código)** — `apps/worker/`: FastAPI (`POST /jobs`, `GET /health`), LangGraph (load_profile → optimize → generate_slides → parse_validate com retry → render_to_jpeg → upload_assets → finalize), prompts em `apps/worker/prompts/`, Dockerfile + Playwright Chromium, `pyproject.toml` + `.env.example`. **Ressalva:** **TP6** no `tasks.md` fala em retry máximo **2×** para `generate_slides`; o nó `parse_validate` incrementa `retry_count` enquanto `< 3` (pode haver **até 4** execuções de `generate_slides` no pior caso). Ajustar código ou spec se quiser aderência literal. |
| **Fase 3 — Integração** | TI1–TI3 | **Concluída (código + testes)** — `docker-compose.yml` na raiz (postgres + api + worker, healthchecks, `WORKER_*` / `GO_API_URL` / volume `tests/e2e/testdata/profile` → `PROFILE_DATA_ROOT`). **TI1** — `go test -tags=integration` em `apps/api/integration/` (`INTEGRATION_DATABASE_URL`); mock worker + callback; `make test-integration` em `apps/api/Makefile`. **TI2** — `pytest` + `httpx` em `tests/e2e/`; `make e2e` no Makefile da raiz. **TI3** — `apps/api/integration/failure_test.go` (callback erro → `failed`, dispatch 500 → 502 + job `failed`, callback sem `assistantText` → 400). A parte **“frontend trata”** do `tasks.md` depende da **Fase 4 (T30)** — ainda não há app React no repo. |
| Fase 4 — Frontend | T24–T33 | Pendente |
| Fase 5 — Cron | T34–T35 | Pendente |
| Fase 6 — QA & Deploy | T36–T41 | Pendente |

**Próximo passo sugerido:** **Fase 4 — Frontend (T24–T33)** — UI React com polling de `GET /chats/:id/jobs/:jobId/status`, estados `pending`/`processing`/`done`/`failed` e UX “gerando…” / erro.

**Nota:** Monorepo: API Go em **`apps/api/`**, worker em **`apps/worker/`** (não `backend/` nem `worker/` na raiz). Opcional: marcar checkboxes no `tasks.md` ou alinhar T9/TP6 ao texto da spec.

---

## Histórico de implementação (contexto futuro)

Entradas cronológicas do que foi efetivamente construído em código frente à spec. *Atualizar ao fechar fases.*

### 2026-04-13 — Go API (Fase 1, núcleo)

**Implementado em `apps/api/`:** modelo e migration `jobs`; `POST /chats/:id/messages` assíncrono (persistência mensagem + job, dispatch HTTP ao worker, status `processing` / `failed`); `POST /internal/jobs/:id/complete` (API key `X-Worker-API-Key`); `GET /chats/:id/jobs/:jobId/status`; `GET /setup/status`; cliente HTTP `WORKER_URL` + `WORKER_API_KEY`; `apps/api/Dockerfile` sem Playwright/Chromium.

**Removido do repo (legado):** `internal/agent/`, `internal/export/`, `backend/promptdata/`, `scripts/sync-promptdata.sh`, alvo `make prompts-sync`. Dependência `langchaingo` retirada do `go.mod`.

**README:** prompts documentados como vivendo em `.cursor/` para referência; runtime do worker usa `apps/worker/prompts/`.

### 2026-04-13 — Worker Python (Fase 2, TP1–TP11)

**Implementado em `apps/worker/`:** projeto instalável (`pyproject.toml`, Hatchling), `Dockerfile` (Python 3.12-slim, `uv`, Playwright + Chromium), `.env.example`. Pipeline LangGraph: `load_profile` → `optimize_prompt` (gpt-4o-mini + `prompts/optimize_prompt.md`) → `generate_slides` (`prompts/generate_slides.md`) → `parse_validate` (marcadores `###SLIDE_FILE:` / `###END_SLIDE###`, retries condicionais) → `render_to_jpeg` (768×1376, JPEG q=92) → `upload_assets` (boto3 S3, **put_object** com até 3 tentativas e backoff) → `finalize` (`httpx` → `POST {GO_API_URL}/internal/jobs/{id}/complete`). FastAPI: `POST /jobs` (202 + `BackgroundTasks` + `graph.ainvoke`), `GET /health`, validação `X-Worker-API-Key`.

**Prompts:** conteúdo operacional em `apps/worker/prompts/*.md` (derivado das regras em `.cursor/`); não há leitura direta de `.cursor/` em runtime na imagem.

### 2026-04-13 — Integração Go ↔ Python (Fase 3, TI1–TI3)

**Infra:** `docker-compose.yml` (Postgres 16, API Go, worker Python) com healthchecks, `WORKER_API_KEY` compartilhada, `GO_API_URL=http://api:8080`, `WORKER_URL=http://worker:8000`, bind mount `tests/e2e/testdata/profile` → `/profile-data` na API. Imagem da API com `wget` para healthcheck.

**TI1:** `apps/api/integration/` — `go test -tags=integration` (Postgres via `INTEGRATION_DATABASE_URL`), mock worker HTTP que valida `X-Worker-API-Key` e payload `DispatchPayload`, callback assíncrono para o Echo em teste; storage mock para `GetSignedURL`; `testdata/AUDIT.md` + `BRAND.md`; alvo `make test-integration` em `apps/api/Makefile`.

**TI2:** `tests/e2e/` — `pytest` + `httpx`, `E2E_API_URL` (default `http://localhost:8080`), fixtures criam perfil em disco por `user_id`; `make e2e` no Makefile da raiz (compose up → pytest → down). Requer credenciais reais (`OPENAI_API_KEY`, AWS/S3) no ambiente ao rodar o stack.

**TI3:** `apps/api/integration/failure_test.go` — erro no callback (`failed` + mensagem), worker retorna 500 no dispatch (502 + job `failed` no DB), callback `{}` sem `assistantText` → 400 no endpoint interno. Tratamento no **frontend** para `failed` fica na Fase 4.

### 2026-04-12 — Reescrita da spec (Go API + LangGraph)

**Objetivo:** Documentar dois serviços — API Go (CRUD, auth, jobs, callback) **sem** `internal/agent/` / `internal/export/` no desenho alvo; processamento em **`apps/worker/`** (Python, LangGraph, Playwright, S3). Contrato: `POST /chats/:id/messages` → `202` + `jobId`; `POST /internal/jobs/:id/complete` no Go.

**Documentação atualizada:** `spec.md`, `design.md`, `tasks.md` (reescrito), `STATE.md`, `docs/PRD.md`, `docs/TDD.md`.

---

## Trabalho em progresso

| Feature | Marco | Notas |
|---------|--------|-------|
| content-creator-agent | Fase 4 Frontend | Contrato API + integração Go/worker prontos; iniciar T24+ conforme `tasks.md`. |
| content-creator-agent | Opcional | Fechar gaps menores T9 (`DeleteMany` backoff) e TP6 (contagem de retry) se quiser aderência literal ao `tasks.md`. |

## Decisões registradas

| # | Decisão | Contexto | Data |
|---|---------|----------|------|
| 1 | Limite de 5 chats: remoção automática do mais antigo ao criar o 6º | Usuário pode deletar manualmente qualquer chat | 2026-04-10 |
| 2 | Redis: rate limiting em memória no V1 (Redis opcional) | Redis pode ser adotado para escala horizontal no V2 | 2026-04-10 |
| 3 | JWT: refresh token em cookie httpOnly + Secure + SameSite=Strict; access token em memória no cliente | Nunca em localStorage para proteção XSS | 2026-04-10 |
| 4 | Geração de slides: GPT-5.4 Mini → HTML/CSS → Playwright → JPEG (768×1376px, qualidade 92) | Sem modelo dedicado de geração de imagem | 2026-04-10 |
| 5 | Limite de 4.000 tokens de saída por requisição ao LLM | Estimativa conservadora; revisar com dados reais de produção | 2026-04-10 |
| 6 | Cookie `Secure` em `COOKIE_SECURE` (default true em produção; `false` para HTTP local) | Permite testar login/refresh em dev sem HTTPS | 2026-04-12 |
| 7 | System prompts: referência em `.cursor/` skills/rules; **sem** `backend/promptdata/` — o worker em runtime lê **`apps/worker/prompts/*.md`** na imagem (alinhar mudanças de skills com essa pasta) | Evita duplicar sync para o Go | 2026-04-13 |
| 8 | **Arquitetura do zero: Go = API/CRUD/jobs em `apps/api/` (sem agent/export no desenho alvo); Python + LangGraph = motor em `apps/worker/`.** | **`docs/architecture-go-api-langgraph.md`** | **2026-04-12** |

## Bloqueadores ativos

Nenhum.

## Ideias adiadas (deferred)

| Ideia | Motivo do adiamento | Fase alvo |
|-------|---------------------|-----------|
| Tela de configuração de perfil (upload de referências visuais) | Fora do escopo V1 | V2 |
| Publicação direta no Instagram via API | Fora do escopo V1 | V2 |
| Redis para rate limiting e cache de sessões | Opcional no V1 | V2 |
| Histórico expandido (mais de 5 posts) | Fora do escopo V1 | V2 |
| Expansão para outros formatos (Reels, Stories) | Fora do escopo V1 | V2 |
| Cloudflare R2 como alternativa ao S3 | Alternativa viável | V2 |

## Lições aprendidas

| Data | Lição |
|------|-------|
| 2026-04-12 | Build Docker do backend legado incluía Playwright + Chromium — na nova arquitetura, Chromium fica no **worker** Python. |
| 2026-04-12 | Alterar skills em `.cursor/` implica alinhar prompts carregados pelo worker. |
| 2026-04-13 | Remover `promptdata/` simplifica o repo: uma fonte (`.cursor/`) até o worker definir empacotamento em imagem ou CI. |
| 2026-04-13 | Prompts de execução do worker ficam em `apps/worker/prompts/` na imagem; alinhar alterações em `.cursor/rules` com cópias/atualizações nessa pasta quando necessário. |
| 2026-04-13 | Integração: testes Go com tag `integration` exigem Postgres acessível (`INTEGRATION_DATABASE_URL`); E2E com compose exige credenciais LLM/S3 no host — sem isso o worker só sobe healthy; o fluxo completo falha no job. |

## Contexto de sessão (referência rápida)

- **TDD:** `docs/TDD.md`
- **Stack alvo:** Go/Echo (`apps/api/`) + React + PostgreSQL + S3 + **Python (LangGraph, FastAPI, Playwright, boto3)** em `apps/worker/`
- **Contrato:** ver `design.md` — seção **Contrato Go ↔ Python**
