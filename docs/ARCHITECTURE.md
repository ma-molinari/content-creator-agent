# Architecture

**Pattern:** Modular monorepo — three independent services (Go API, Python Worker, React SPA) wired by Docker Compose and a shared AWS S3 bucket.

## High-Level Structure

```
┌─────────────┐        HTTPS / REST        ┌──────────────────────┐
│  React SPA  │ ◄────────────────────────► │   Go API (Echo)      │
│  (Vite/TS)  │   Bearer JWT + HttpOnly     │   :8080              │
└─────────────┘   refresh cookie            └──────────┬───────────┘
                                                        │ POST /jobs (HTTP, shared API key)
                                                        ▼
                                             ┌──────────────────────┐
                                             │  Python Worker       │
                                             │  (FastAPI + LangGraph│
                                             │  + Playwright)       │
                                             │  :8000               │
                                             └──────────┬───────────┘
                                                        │ POST :8081/internal/jobs/:id/complete
                                                        ▼ (callback to Go API)
                                             ┌──────────────────────┐
                                             │   PostgreSQL 16      │
                                             └──────────────────────┘
                                                        │
                                             ┌──────────────────────┐
                                             │   AWS S3             │
                                             │  (slides + refs)     │
                                             └──────────────────────┘
```

## Identified Patterns

### Repository / Service / Handler triple (Go API)

**Location:** every domain package under `apps/api/internal/*`
**Purpose:** clean separation between transport, business logic, and data access.
**Implementation:**
- `handler.go` — Echo route handlers; binds request, calls service, maps errors to HTTP codes
- `service.go` — business logic, orchestrates repositories and external clients
- `repository.go` — GORM queries; returns typed structs, translates `ErrRecordNotFound` to `nil`
- `service_test.go` — unit tests using SQLite in-memory via `db.ConnectWithURL("sqlite://…")`

**Example:** `apps/api/internal/auth/{handler,service,repository}.go`

### Async Job pattern (fire-and-forget + poll)

**Location:** `apps/api/internal/jobs/`, `apps/worker/app/main.py`
**Purpose:** offload long-running generation work without blocking the HTTP request.
**Implementation:**
1. `POST /chats/:id/messages` → creates `Job{status: processing}` in DB, dispatches `POST /jobs` to worker, returns `202 {jobId}`.
2. Worker receives the dispatch, starts a FastAPI `BackgroundTask` running the LangGraph graph.
3. On completion the worker calls back `POST /internal/jobs/:id/complete` (authenticated by shared `X-Worker-API-Key`), which persists the assistant message + slide image records inside a DB transaction and sets `status: done` (or `failed`).
4. Frontend polls `GET /chats/:id/jobs/:jobId/status` until terminal status.

### Fluxo estruturado experimental

Com `STRUCTURED_POSTS_ENABLED` habilitada e cliente compatível, novos chats podem usar `structured_v1`. A API verifica todos os destinos diretos em `STRUCTURED_WORKER_URLS` e despacha para `/jobs/structured`; o legado continua em `WORKER_URL/jobs`. O worker gera ou edita um documento tipado, copia assets autorizados para o prefixo do job e publica snapshot, manifesto, HTML e JPEG. O callback valida os objetos e avança o ponteiro de versão sob locks de chat/job; concorrência obsoleta falha com `VERSION_CONFLICT`. A flag fica desligada por padrão e não deve ser habilitada antes da aceitação operacional e visual. Consulte `docs/RUNBOOK.md`.

### LangGraph pipeline (Python Worker)

**Location:** `apps/worker/app/graph.py`, `apps/worker/app/nodes/`
**Purpose:** structured multi-step AI workflow with conditional retry.
**Fluxo legado:** `prepare_input` → `security_validate` → `profile_overview` → `intent_detect`. Em edição, `load_existing_slides` recupera os HTMLs anteriores. Em seguida: `attachment_analyze` → `build_generation_plan` → `generate_or_edit_slides` → `validate_slide_package` → `validate_design` → `validate_attachment_usage` → `render_and_contrast` → `upload_assets` → `finalize`. As validações podem solicitar nova geração ou encerrar com falha. O worker tenta informar progresso à API antes de cada etapa; operações longas sem novos eventos podem exceder o limite da limpeza. O HTML e os JPEGs são armazenados no S3; Playwright renderiza em 1080×1350.

### JWT dual-token auth

**Location:** `apps/api/internal/auth/`, `apps/api/internal/middleware/jwt.go`
**Purpose:** short-lived access token + long-lived refresh token held in HttpOnly cookie.
- Access token: HS256, 4 h, sent as `Authorization: Bearer` header
- Refresh token: HS256, 7 days, set as HttpOnly cookie on login
- Middleware `appmw.JWT()` validates the access token on every protected route
- Frontend `axios` interceptor silently refreshes on 401 and retries the failed request via a pending queue

### User Profile & Setup gate

**Location:** `apps/api/internal/profile/`, `chat/post_message.go`
**Purpose:** users must fill in `audit_text` and `brand_text` before sending messages.
- `GET /setup/status` → `{configured: bool}` (both texts non-empty)
- `POST /chats/:id/messages` returns `400 SETUP_REQUIRED` if profile is incomplete
- Optional design reference images (up to 8, 5 MB each) stored in S3; keys persisted in `user_profile_references`

### Security layers

- Auth routes: IP-based rate limit (20 req / 5 min, `ulule/limiter` in-memory)
- LLM routes: per-user rate limit (20 req / 1 min)
- CORS: explicit origin allowlist (`CORS_ALLOWED_ORIGINS` env); no wildcard
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
- Worker callback: protected by shared `WORKER_API_KEY` header
- S3 artifact key validation: enforces `slides/{jobId}/` prefix, rejects `..` and absolute paths

## Data Flow

### Message → Slide generation

```
User types message
  → POST /chats/:id/messages (Bearer token)
  → [API] creates user ChatContent row
  → [API] creates Job{status: processing}
  → [API] POST http://worker:8000/jobs  (X-Worker-API-Key)
  → [API] returns 202 {jobId}
  → [Worker] LangGraph ainvoke in background task
  → [Worker] render slides → JPEG → upload to S3
  → [Worker] POST http://api:8081/internal/jobs/:id/complete
  → [API] DB transaction: create assistant ChatContent + ChatContentImage rows, set Job{done}
  → User polls GET /chats/:id/jobs/:jobId/status → "done"
  → Frontend loads updated chat thread
```

### Authentication flow

```
Register → returns securityKey (shown once, used only for password recovery)
Login    → sets refresh cookie (HttpOnly) + returns accessToken in JSON body
           Frontend stores accessToken in Zustand (in-memory only, never localStorage)
Request  → axios interceptor adds Bearer header
401      → interceptor calls POST /auth/refresh (cookie auto-sent)
           → on success: update Zustand + retry original request
           → on failure: clear store + redirect to /login
```

## Code Organization

**Approach:** feature/domain-based inside each app.

### Go API
```
cmd/server/main.go         # wiring: instantiate all repos/services/handlers, register routes
internal/
  auth/                    # registration, login, refresh, password recovery
  chat/                    # chat CRUD, message posting, file/zip download, job status
  config/                  # env-based Config struct
  cron/                    # scheduler wrapper (robfig/cron)
  db/                      # GORM connection, migration runner, model definitions
  httperr/                 # Internal() helper: log real error, return 500
  jobs/                    # job repository, worker HTTP client, complete handler, key validation
  middleware/              # JWT, CORS, security headers, rate limiters
  profile/                 # user profile + design references
  storage/                 # S3 interface + implementation
integration/               # integration tests (build tag: integration)
```

### Python Worker
```
app/
  main.py       # FastAPI app, /jobs dispatch, /health
  config.py     # pydantic-settings Config
  graph.py      # LangGraph graph construction
  state.py      # AgentState TypedDict
  nodes/        # one file per graph node
prompts/        # system prompt markdown files (read at runtime)
```

### React SPA
```
src/
  api/          # domain API modules (auth, chats, profile) + axios client
  components/   # UI components grouped by feature (auth, chat, composer, shell, slides, ui)
  lib/          # shared utilities (queryClient, toast, crypto)
  pages/        # page-level components (Chat, History, Login, Register, ProfileSettings)
  router/       # react-router-dom route definitions
  stores/       # zustand stores (auth)
```
