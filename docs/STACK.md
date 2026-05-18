# Tech Stack

**Analyzed:** 2026-04-25

## Core

- Monorepo layout: `apps/api`, `apps/worker`, `apps/web`
- Container orchestration: Docker Compose (dev + prod overlay)
- Package manager (web): npm
- Package manager (worker): uv

## Backend — API (`apps/api`)

- Language: Go 1.25 (declared in `go.mod`; likely meant 1.24)
- Framework: Echo v4.12.0
- ORM: GORM v1.30.0 with `gorm.io/driver/postgres` v1.5.9
- DB driver: `jackc/pgx/v5` v5.7.2
- Database: PostgreSQL 16 (Alpine image in Docker Compose)
- Migrations: `golang-migrate/migrate/v4` v4.18.1 (SQL files, applied at startup)
- Authentication: `golang-jwt/jwt/v5` v5.2.1, `golang.org/x/crypto/bcrypt`
- Rate limiting: `ulule/limiter/v3` v3.11.2 (in-memory store)
- Scheduling: `robfig/cron/v3` v3.0.1
- Storage client: `aws/aws-sdk-go-v2/service/s3` v1.99.0
- ID generation: `google/uuid` v1.6.0
- Test assertion: `stretchr/testify` v1.11.1
- SQLite (test only): `gorm.io/driver/sqlite` v1.6.0

## Backend — Worker (`apps/worker`)

- Language: Python ≥ 3.9
- API framework: FastAPI ≥ 0.115.0 + Uvicorn ≥ 0.32.0
- Agent orchestration: LangGraph ≥ 0.2.0
- LLM SDK: LangChain-OpenAI ≥ 0.2.0, LangChain-Core ≥ 0.3.0
- LLM defaults: worker chat + vision **`gpt-5.4`** (`OPENAI_CHAT_MODEL`, `REFERENCE_VISION_MODEL`). Details: `docs/INTEGRATIONS.md`.
- HTML → image rendering: Playwright ≥ 1.49.0 (headless Chromium)
- AWS client: boto3 ≥ 1.35.0
- HTTP client: httpx ≥ 0.27.0
- Configuration: pydantic-settings ≥ 2.6.0
- Dev linter: ruff ≥ 0.8.0
- Build backend: hatchling

## Frontend (`apps/web`)

- Framework: React 19.2.4
- Language: TypeScript ~6.0.2
- Router: React Router v7.14.1
- Data fetching / cache: TanStack React Query v5.99.0
- Global state: Zustand v5.0.12
- HTTP client: axios v1.15.0
- Styling: Tailwind CSS v4.2.2 (Vite plugin, no config file)
- Build tool: Vite v8.0.4
- Lint: ESLint v9 + eslint-plugin-react-hooks + react-refresh

## Testing

- Unit (API): `go test ./...` using testify + SQLite in-memory DB
- Integration (API): `go test -tags=integration ./integration/...` against a real Postgres instance (`INTEGRATION_DATABASE_URL`)
- E2E (full stack): pytest + httpx (`tests/e2e/`) against Docker Compose
- Screenshots (web): Playwright via `npm run screenshots` inside `apps/web`

## External Services

- Object storage: AWS S3 (slide JPEG uploads, profile reference images)
- AI/LLM: OpenAI API (slide generation and vision via worker)
- Container runtime: Docker (Docker Compose for local + prod)

## Development Tools

- Root Makefile: orchestrates `docker compose up`, E2E tests, prod deploy
- API Makefile: `run`, `build`, `test`, `test-integration`, migrations (`migrate-up/down/version`)
- Migration runner: `go run` (no external binary required)
