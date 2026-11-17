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

### 2. Expiração de URLs S3 persistidas

**Files:** `apps/api/internal/jobs/complete.go`, `apps/api/internal/db/models.go`
**Evidence:**
```go
const signedURLExpiry = time.Hour
url, err := store.GetSignedURL(ctx, key, signedURLExpiry)
// ...
img := db.ChatContentImage{ URL: url, ... }
tx.Create(&img)
```
URLs armazenadas expiram; o serviço renova URLs ao carregar o chat e a interface atualiza periodicamente os dados. Consumidores não devem depender indefinidamente da URL persistida; usem a chave S3 e os endpoints autenticados.

---

### 3. Jobs can remain stuck until cleanup (`processing`)

**Files:** `apps/api/internal/chat/post_message.go`, `apps/api/internal/jobs/`
**Evidence:** Jobs are marked `processing` before the worker dispatch returns. If dispatch fails, the API sets `failed`. If the worker accepts the job and then crashes (or the container OOMs during LangGraph), the callback may never run and the row can remain `processing`. A cron marks jobs in `processing` without a recent heartbeat or update as `failed` (`RunStuckJobCleanup` / `FailStuckProcessingJobs`).

Previously, the API moved a job to `processing` only *after* a successful dispatch; if that status update failed after dispatch succeeded, the job could remain `pending` while the worker had already accepted work — the callback rejects non-`processing` jobs. That ordering is fixed: `processing` is set before dispatch.
**Risk:** A etapa legítima que exceder o limite sem atualizar o heartbeat também pode ser marcada como falha. User-visible stuck or failed jobs after worker incidents; transient API errors during dispatch can still flip a job to `failed` after a brief `processing` state.
**Fix (remaining):** Optional dead-letter retry; stronger idempotency if the worker may run the same job twice.

---

### 4. Refresh token server-side session (rotation races mitigated)

**Files:** `apps/api/internal/auth/service.go`, `apps/api/internal/auth/repository.go`, `apps/api/cmd/server/main.go`
**Evidence:**
```go
// RevokeAndCreateRefreshToken: UPDATE … WHERE jti = ? AND revoked_at IS NULL; RowsAffected must be 1
// Cron: DeleteExpiredRefreshTokens at 03:00 UTC
```
Refresh JWTs embed a JTI persisted in `refresh_tokens`. Login inserts a row; `/auth/refresh` revokes the current JTI and inserts the next in one transaction — **only if exactly one active row was revoked**, so concurrent refresh with the same cookie yields **401** for the loser instead of two valid refresh tokens. Logout revokes the current JTI.
**Residual risk:** DB outage or manual inconsistency could leave JWT and row out of sync; token purge removes expired rows but does not replace full session audit tooling.
**Fix (optional hardening):** Device/session lists, revoke-all, anomaly alerts.

---

## MEDIUM — Data Integrity / Correctness

### 5. Compatibilidade da versão Go

`apps/api/go.mod` declara Go 1.25. Confirme que imagens e ambientes de desenvolvimento suportam a versão declarada antes de alterar dependências.

---

### 6. No pagination on chat listing and message retrieval

**Files:** `apps/api/internal/chat/handler.go`, `apps/api/internal/chat/repository.go`
**Evidence:** `GET /chats` returns up to five chats for a user; `GET /chats/:id` returns the full `Contents` slice with all messages. No `limit` / `offset` / `cursor` parameters.
**Risk:** As a user accumulates messages, response sizes grow unbounded. Memory pressure on the API and slow frontend rendering.
**Fix:** Add pagination for message retrieval if conversation sizes warrant it.

---

### 7. Concorrência do worker

As chamadas LLM atuais usam `ainvoke` e as principais operações S3 bloqueantes usam `asyncio.to_thread`. A capacidade e a concorrência de jobs ainda devem ser avaliadas sob carga.

---

## LOW — Security / Hardening

### 8. S3 key path-traversal validation is in the jobs callback only

**File:** `apps/api/internal/jobs/slide_key.go`
**Evidence:** `validateSlideArtifactKey` is called only in `CompleteAssistantReply`. Profile reference upload paths are not validated with the same strictness (not verified in code review — warrants audit).
**Risk:** If profile reference keys are not sanitized before storage, a malicious payload could reference arbitrary S3 paths.
**Fix:** Apply key validation consistently across all S3 operations that accept keys from external inputs.

---

### 9. No CI/CD configuration committed

**Evidence:** No `.github/`, `.gitlab-ci.yml`, or similar CI files are present in the repository. Tests are manually triggered or via `make e2e`.
**Risk:** No automated gate prevents broken builds or failed tests from reaching production.
**Fix:** Add a CI pipeline (GitHub Actions or equivalent) that runs `go test ./...`, `go vet ./...`, and optionally integration tests on PRs targeting the main branch.

---
