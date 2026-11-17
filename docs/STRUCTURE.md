# Project Structure

**Root:** `/content-creator-agent`

## Directory Tree

```
content-creator-agent/
├── Makefile                         # Root orchestration: e2e, prod-up, prod-down
├── docker-compose.yml               # Dev stack: postgres + api + worker
├── docker-compose.prod.yml          # Prod overlay (port/env overrides)
├── package.json                     # Root workspace metadata (no root npm dependencies)
├── docs/                            # Architecture, PRD, TDD, ui-guidelines, UI screenshots
├── tests/
│   └── e2e/                         # Full-stack E2E (pytest + httpx)
│       ├── conftest.py
│       ├── test_smoke.py
│       └── requirements.txt
├── apps/
│   ├── api/                         # Go REST API
│   ├── worker/                      # Python LangGraph worker
│   └── web/                         # React SPA
└── .specs/                          # Feature specs (create-spec-driven workflow)
    └── features/content-creator-agent/
```

## Module Organization

### `apps/api` — Go REST API

**Purpose:** user management, chat persistence, job dispatch, file delivery.

```
apps/api/
├── cmd/server/main.go               # Entry point: wire deps, register routes, graceful shutdown
├── Makefile                         # run, build, test, test-integration, migrate-*
├── Dockerfile
├── .env.example
├── go.mod / go.sum
└── internal/
│   ├── auth/                        # Registration, login, refresh, password recovery
│   │   ├── handler.go
│   │   ├── service.go
│   │   ├── repository.go
│   │   └── service_test.go
│   ├── chat/                        # Chat CRUD, PostMessage (async dispatch), file download
│   │   ├── handler.go
│   │   ├── service.go
│   │   ├── repository.go
│   │   ├── post_message.go          # PostMessage business logic
│   │   ├── profile.go               # Chat ↔ profile helpers
│   │   └── service_test.go
│   ├── config/                      # Config struct loaded from env
│   ├── cron/                        # Cron scheduler wrapper (robfig/cron)
│   ├── db/
│   │   ├── models.go                # All GORM model structs
│   │   ├── db.go                    # GORM connection factory
│   │   ├── migrate.go               # golang-migrate runner
│   │   └── migrations/              # Numbered SQL up/down files (001–016)
│   ├── httperr/                     # Internal(prefix, err) → 500 helper
│   ├── jobs/
│   │   ├── handler.go               # POST /internal/jobs/:id/complete
│   │   ├── complete.go              # CompleteAssistantReply transaction
│   │   ├── repository.go            # Job DB queries
│   │   ├── worker_client.go         # HTTPWorkerClient (dispatches to Python worker)
│   │   └── slide_key.go             # S3 key validation (path traversal prevention)
│   ├── middleware/
│   │   ├── jwt.go                   # Bearer token validation, UserID context key
│   │   ├── rate_limit.go            # AuthByIP (20/5min), LLMByUser (20/1min)
│   │   └── security.go              # Security headers + CORS allowlist
│   ├── profile/
│   │   ├── handler.go               # GET/PUT /profile, POST/DELETE /profile/references
│   │   ├── service.go               # Profile + reference business logic
│   │   ├── repository.go            # UserProfile DB queries
│   │   └── references_repository.go # UserProfileReference DB queries
│   ├── storage/
│   │   └── s3.go                    # StorageService interface + S3 implementation
└── integration/                     # Integration tests (build tag: integration)
    ├── helpers_test.go              # newTestEnv, buildEcho, registerAndLogin helpers
    ├── auth_test.go
    ├── chat_crud_test.go
    ├── dispatch_test.go             # End-to-end job dispatch + callback tests
    ├── failure_test.go
    ├── profile_test.go
    └── security_test.go
```

### `apps/worker` — Python LangGraph Worker

**Purpose:** AI pipeline — planning, HTML slide generation and editing, Playwright rendering, S3 upload, callback.

```
apps/worker/
├── app/
│   ├── main.py              # FastAPI app: POST /jobs, GET /health
│   ├── config.py            # pydantic-settings Config
│   ├── graph.py             # LangGraph StateGraph construction
│   ├── state.py             # AgentState TypedDict (incl. design_retry_count)
│   ├── slide_design_checks.py  # Static HTML/CSS checks (no JS, remote assets, fonts, viewport)
│   └── nodes/
│       ├── prepare_input.py             # Prepara entrada recebida da API
│       ├── security_validate.py  # Deterministic safety gate on raw user message
│       ├── intent_detect.py              # Detecta criação ou refinamento
│       ├── build_generation_plan.py      # Plano de geração e anexos
│       ├── generate_or_edit_slides.py    # Gera ou edita HTML dos slides
│       ├── validate_slide_package.py    # Valida pacote de slides
│       ├── validate_design.py           # Valida HTML e CSS
│       ├── render_and_contrast.py       # Playwright e correção de contraste
│       ├── upload_assets.py             # boto3 S3 upload
│       └── finalize.py                  # Callback to Go API + assemble caption
├── prompts/             # System prompt markdown files (loaded at runtime)
├── tests/
│   └── test_slide_design_checks.py  # Unit tests for static design check functions
├── pyproject.toml
├── Dockerfile
└── .env.example
```

### `apps/web` — React SPA

**Purpose:** user-facing chat interface, auth flows, profile settings, slide viewer.

```
apps/web/src/
├── main.tsx             # React root, QueryClientProvider
├── App.tsx              # App shell: QueryClientProvider + AppRouter + ToastContainer
├── api/
│   ├── client.ts        # axios instance + JWT interceptor + refresh retry
│   ├── auth.ts          # register, login, refresh, recoverPassword
│   ├── chats.ts         # list, create, get, delete, postMessage, jobStatus, files
│   └── profile.ts       # get, save, postReference, deleteReference
├── components/
│   ├── auth/            # AuthSplitLayout, ProtectedRoute, SecurityKeyModal
│   ├── chat/            # ChatThread, MessageAssistant, MessageBubbleUser, JobStatusIndicator
│   ├── composer/        # ComposerBar (message input)
│   ├── profile/         # ProfileBrandGuide
│   ├── shell/           # AppShell, SidebarRail, NavItem
│   ├── slides/          # SlideViewer, AuthenticatedSlideImage
│   └── ui/              # AlertDialog, ToastContainer
├── lib/
│   ├── queryClient.ts   # TanStack Query client config
│   ├── toast.ts         # Toast helper
│   └── sanitizeUserInput.ts  # Input sanitization
├── pages/
│   ├── Chat.tsx
│   ├── History.tsx
│   ├── Login.tsx
│   ├── Register.tsx
│   ├── RecoverPassword.tsx
│   └── ProfileSettings.tsx
├── router/
│   └── index.tsx        # React Router routes + ProtectedRoute guards
└── stores/
    └── auth.ts          # Zustand auth store (access token, in-memory only)
```

## Where Things Live

**Authentication:**
- UI: `apps/web/src/pages/Login.tsx`, `Register.tsx`, `components/auth/`
- Business Logic: `apps/api/internal/auth/service.go`
- Data Access: `apps/api/internal/auth/repository.go`
- Token transport: `apps/web/src/api/client.ts` (interceptor), `apps/web/src/stores/auth.ts`

**Content generation (carousel/slide):**
- UI: `apps/web/src/pages/Chat.tsx`, `components/chat/`, `components/slides/`, `components/composer/`
- Dispatch: `apps/api/internal/chat/post_message.go`, `apps/api/internal/jobs/worker_client.go`
- AI pipeline: `apps/worker/app/graph.py`, `apps/worker/app/nodes/`
- Completion callback: `apps/api/internal/jobs/complete.go`

**Profile & brand:**
- UI: `apps/web/src/pages/ProfileSettings.tsx`, `components/profile/`
- Logic: `apps/api/internal/profile/service.go`
- Data: `apps/api/internal/profile/repository.go`, `references_repository.go`

**Database schema:**
- Models: `apps/api/internal/db/models.go`
- Migrations: `apps/api/internal/db/migrations/` (001–016)

**Infrastructure / configuration:**
- Docker: `docker-compose.yml`, `docker-compose.prod.yml`
- API env: `apps/api/.env.example`
- Worker env: `apps/worker/.env.example`
- Web env: `apps/web/.env.example` (VITE_API_BASE_URL)

## Special Directories

**`docs/`:**
Architecture docs, PRD, TDD, UI guidelines (layout + tokens), UI mockups. The 7 codebase map files produced by this analysis also live here.

**`.specs/`:**
Feature specification files generated by the `create-spec-driven` skill. Tracks implementation state in `.specs/STATE.md`.

**`tests/e2e/`:**
Root-level full-stack E2E against a live Docker Compose stack (real LLM + S3 calls). Orchestrated by the root `Makefile`.
