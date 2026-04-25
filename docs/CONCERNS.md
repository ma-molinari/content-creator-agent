# Concerns

## HIGH — Correctness / Reliability

### 1. In-memory rate limiters — incorrect behavior when horizontally scaled

**Files:** `apps/api/internal/middleware/rate_limit.go`
**Evidence:**
```go
store := memory.NewStore()
instance := limiter.New(store, rate)
```
Both `AuthByIP` and `LLMByUser` use `ulule/limiter` backed by an in-memory store. Each API process maintains its own independent counter. Running two or more API replicas means the effective rate limit is `N × configured_limit`.
**Risk:** Auth brute-force and LLM abuse protections silently degrade under horizontal scale.
**Fix:** Replace `memory.NewStore()` with a Redis-backed store (`ulule/limiter/v3/drivers/store/redis`) and provision a Redis instance in Docker Compose. Single-replica deployments are not affected.

---

### 2. Stale signed S3 URLs in the database

**Files:** `apps/api/internal/jobs/complete.go`, `apps/api/internal/db/models.go`
**Evidence:**
```go
const signedURLExpiry = time.Hour
url, err := store.GetSignedURL(ctx, key, signedURLExpiry)
// ...
img := db.ChatContentImage{ URL: url, ... }
tx.Create(&img)
```
Presigned URLs are generated once on job completion and persisted in `chat_content_image.url`. After 1 hour the stored URL becomes invalid; any frontend fetch of old chats will receive 403/expired responses from S3.
**Risk:** Broken slide images for chats older than 1 hour; poor UX on returning users.
**Fix options:**
- Generate presigned URLs on-the-fly in `GetChat` / `ListFiles` rather than persisting them (store only `s3_key`)
- Or store only `s3_key` in DB and add a `GET /chats/:id/files/:fileId/url` endpoint that returns a fresh presigned URL

---

### 3. Jobs can stay permanently in `pending` state

**Files:** `apps/api/internal/chat/post_message.go`, `apps/api/internal/jobs/`
**Evidence:** When the Go API dispatches to the worker and receives a `202`, the job is set to `processing`. If the worker crashes after accepting the job (or the Docker container OOMs during a long LangGraph run), no mechanism resets or retries the job. The `cron` scheduler only handles chat summarization.
**Risk:** User-visible "stuck" jobs; manual DB intervention required to recover.
**Fix:** Add a cron job (or startup check) that marks jobs stuck in `processing` for more than N minutes as `failed`. Optionally add a dead-letter retry mechanism.

---

### 4. No refresh token rotation or revocation

**Files:** `apps/api/internal/auth/service.go`
**Evidence:**
```go
refreshTokenTTL = 7 * 24 * time.Hour
```
Refresh tokens are stateless JWTs stored only in HttpOnly cookies. There is no refresh token table, no rotation on use, and no revocation mechanism.
**Risk:** A stolen refresh token remains valid for up to 7 days. There is no way to log out all sessions or invalidate a compromised token server-side.
**Fix:** Store refresh token hashes in a `refresh_tokens` table; rotate on each `/auth/refresh` call (issue new token, invalidate old); add a `DELETE /auth/logout` endpoint that deletes the DB row.

---

## MEDIUM — Data Integrity / Correctness

### 5. `go.mod` declares `go 1.25.0` which does not exist

**File:** `apps/api/go.mod`
**Evidence:** `go 1.25.0` — Go 1.25 has not been released as of 2026-04-25. Go releases are 1.22, 1.23, 1.24.
**Risk:** Some tooling (`go mod tidy`, CI, Dockerfile) may warn or fail. The declared Go version affects language feature availability and `godoc` interpretation.
**Fix:** Update to the actual version in use (likely `go 1.24.0` or `go 1.23.x`).

---

### 6. No pagination on chat listing and message retrieval

**Files:** `apps/api/internal/chat/handler.go`, `apps/api/internal/chat/repository.go`
**Evidence:** `GET /chats` returns all chats for a user; `GET /chats/:id` returns the full `Contents` slice with all messages. No `limit` / `offset` / `cursor` parameters.
**Risk:** As a user accumulates chats and messages, response sizes grow unbounded. Memory pressure on the API and slow frontend rendering.
**Fix:** Add cursor-based or offset pagination on `GET /chats` and `GET /chats/:id/messages`.

---

### 7. Summarizer runs in the same process as the HTTP server with blocking DB queries

**Files:** `apps/api/internal/summarizer/service.go`, `apps/api/internal/cron/scheduler.go`
**Evidence:** The cron fires `summSvc.Run(context.Background())` synchronously inside a goroutine spawned by robfig/cron. The run calls OpenAI (`Summarize`) and performs DB writes for every eligible chat within a 5-minute budget.
**Risk:** Under load, many simultaneous OpenAI calls (one per eligible chat) from the summarizer can exhaust the DB connection pool or the process's goroutine count, degrading API latency.
**Fix:** Rate-limit OpenAI calls within the summarizer (e.g., `golang.org/x/time/rate`), or move summarization to a separate worker/job queue.

---

### 8. Worker slide-generation node is synchronous (`llm.invoke`)

**File:** `apps/worker/app/nodes/generate_slides.py`
**Evidence:**
```python
msg = llm.invoke([SystemMessage(...), HumanMessage(...)])
```
`langchain_openai.ChatOpenAI.invoke` is synchronous. The LangGraph graph is invoked via `await graph.ainvoke(state)`, but this node blocks the event loop during the OpenAI HTTP call.
**Risk:** Each job monopolizes the asyncio event loop for the duration of the LLM call (can be several seconds). If multiple jobs run concurrently (FastAPI `BackgroundTasks` doesn't limit concurrency), the worker may become unresponsive.
**Fix:** Use `llm.ainvoke` (async) or switch the node to `async def` and use the async LangChain API, which is already available in `langchain_openai`.

---

## LOW — Security / Hardening

### 9. S3 key path-traversal validation is in the jobs callback only

**File:** `apps/api/internal/jobs/slide_key.go`
**Evidence:** `validateSlideArtifactKey` is called only in `CompleteAssistantReply`. Profile reference upload paths are not validated with the same strictness (not verified in code review — warrants audit).
**Risk:** If profile reference keys are not sanitized before storage, a malicious payload could reference arbitrary S3 paths.
**Fix:** Apply key validation consistently across all S3 operations that accept keys from external inputs.

---

### 10. No CI/CD configuration committed

**Evidence:** No `.github/`, `.gitlab-ci.yml`, or similar CI files are present in the repository. Tests are manually triggered or via `make e2e`.
**Risk:** No automated gate prevents broken builds or failed tests from reaching production.
**Fix:** Add a CI pipeline (GitHub Actions or equivalent) that runs `go test ./...`, `go vet ./...`, and optionally integration tests on PRs targeting the main branch.

---

### 11. `dist/` directory committed for the web app

**Evidence:** `apps/web/dist` appears in the directory listing.
**Risk:** Committing build artifacts inflates repo size and can cause stale build confusion.
**Fix:** Add `apps/web/dist` to `.gitignore` (if not already present) and remove it from the tree.
