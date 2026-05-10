# Testing Infrastructure

## Test Frameworks

| Layer | Framework | Location |
|-------|-----------|----------|
| Go unit | `testing` + `stretchr/testify` v1.11.1 | `apps/api/internal/**/*_test.go` |
| Go integration | `testing` + `testify` + `net/http/httptest` | `apps/api/integration/` |
| Python E2E | pytest + httpx | `tests/e2e/` |
| Web screenshots | Playwright (`@playwright/test`) | `apps/web/e2e/` |

## Test Organization

### Go Unit Tests

**Location:** co-located with production code, same package.
**Naming:** `<unit>_test.go`.
**Build tag:** none (run by default with `go test ./...`).

Files observed:
- `apps/api/internal/auth/service_test.go`
- `apps/api/internal/chat/service_test.go`
- `apps/api/internal/jobs/repository_test.go`
- `apps/api/internal/jobs/slide_key_test.go`
- `apps/api/internal/profile/service_test.go`
- `apps/api/internal/config/config_test.go`
- `apps/api/internal/db/db_test.go`
- `apps/api/internal/storage/s3_test.go`

**DB approach for repo/service tests:** SQLite in-memory via GORM driver (`gorm.io/driver/sqlite`). Allows running without a Postgres instance.

### Go Integration Tests

**Location:** `apps/api/integration/`
**Build tag:** `//go:build integration` — excluded from the default `go test ./...` run.
**Requirement:** `INTEGRATION_DATABASE_URL` env var (real Postgres). Tests are skipped when unset.

**What they test:**
- `auth_test.go` — register, login, refresh cookie, password recovery
- `chat_crud_test.go` — chat CRUD operations
- `dispatch_test.go` — full async job dispatch + worker callback cycle
- `failure_test.go` — worker error propagation, job status `failed`
- `profile_test.go` — profile save, reference upload/delete
- `security_test.go` — CORS headers, rate limiting

**Test environment setup (`helpers_test.go`):**
`newTestEnv(t, workerHandler)` wires:
1. Real Postgres via `INTEGRATION_DATABASE_URL` (migrations applied)
2. `httptest.NewServer` for the Echo API
3. `httptest.NewServer` for a mock worker (controllable per test)
4. `mockStorage{}` (no real S3; presigned URLs return `https://integration.test/presigned/<key>`)

The mock worker handler receives the dispatch, can call back the real API (`POST /internal/jobs/:id/complete`) to simulate success or failure, enabling end-to-end job lifecycle tests without real LLM or S3.

**Shared helpers:**
- `registerAndLogin(t, env)` → `(accessToken, userID)`
- `createChat(t, env, token)` → `chatID`
- `postMessage(t, env, token, chatID, content)` → `jobID`
- `getJobStatus(t, env, token, chatID, jobID)` → `(status, errMsg)`
- `pollJobDone(t, env, token, chatID, jobID, timeout)` → terminal status

### Python E2E Tests

**Location:** `tests/e2e/`
**Runner:** pytest
**Dependencies:** `httpx`, configured in `tests/e2e/requirements.txt`
**Target:** full Docker Compose stack (`docker compose up -d --build --wait`)

**What they test:**
`test_smoke.py::test_full_post_creation_flow` — exercises the complete user journey:
1. Register user
2. Configure profile (audit + brand text)
3. Create chat
4. Post message → receive `202 {jobId}`
5. Poll `GET /chats/:id/jobs/:jobId/status` (up to 120s) until `done`
6. Assert assistant message + at least one image artifact with an S3 key

This is the only test that calls real OpenAI and writes to real S3.

### Web Screenshot Tests

**Location:** `apps/web/e2e/`
**Framework:** `@playwright/test` v1.59.1
**Config:** `apps/web/playwright.config.ts`
**Command:** `npm run screenshots` (builds Vite first, then runs Playwright)
**Purpose:** capture screenshots of the UI for visual verification / design review (not assertions-based regression tests).

## Test Execution

### API unit tests

```bash
cd apps/api
make test
# equivalent: go test ./...
```

### API integration tests

```bash
export INTEGRATION_DATABASE_URL="postgres://app:app@localhost:5432/content_creator?sslmode=disable"
cd apps/api
make test-integration
# equivalent: go test -tags=integration -v ./integration/...
```

### Full E2E (Docker Compose + real LLM)

```bash
# From repo root — requires .env files with OPENAI_API_KEY, AWS_*, etc.
make e2e
# Runs: docker compose up -d --build --wait && pytest && docker compose down
```

### Web screenshots

```bash
cd apps/web
npm run screenshots
```

## Coverage Targets

**Current:** No coverage tooling or thresholds configured.
**Enforcement:** None automated. CI is not documented in the repository; tests are run manually or via `make e2e`.

## Notable Testing Patterns

- **Integration tests use a mock S3** (`mockStorage{}`). Real S3 is only exercised in full E2E.
- **Worker is mocked per-test** in integration tests via a controllable `httptest.Server`. The handler receives the dispatch and can immediately call back (or simulate delay/failure) without an LLM.
- **SQLite swap for unit tests** keeps unit tests fast and dependency-free (no Docker needed). Schema compatibility with PostgreSQL is tested at the integration layer.
- **E2E tests embed test data** (`testdata/AUDIT.md`, `testdata/BRAND.md`) via Go `//go:embed` to provide realistic profile content without filesystem coupling.
