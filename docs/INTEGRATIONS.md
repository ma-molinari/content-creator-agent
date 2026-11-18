# External Integrations

## Object Storage

**Service:** AWS S3
**Purpose:** Store generated slide JPEG images and user-uploaded design reference images. Serve them to the frontend via time-limited presigned GET URLs.
**Implementation:**
- Interface: `apps/api/internal/storage/s3.go` — `StorageService` interface with `Upload`, `GetSignedURL`, `GetObject`, `Delete`, `DeleteMany`
- Implementation: `S3Service` using AWS SDK v2 (`aws-sdk-go-v2/service/s3`)
- Worker upload: `apps/worker/app/nodes/upload_assets.py` — boto3 `put_object` under `slides/{jobId}/`
**Configuration:**
- `AWS_REGION`, `AWS_S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (all env vars)
- Static credentials via `StaticCredentialsProvider` if key+secret are set; otherwise falls back to default credential chain (IAM role, env, etc.)
**Key conventions:**
- Slide artifacts: `slides/{jobId}/{filename}.jpeg`
- Profile references: unknown key prefix (managed by `profile` package)
- Keys validated server-side against path traversal: no `..`, no `\`, no leading `/`, must start with `slides/{jobId}/`
**Presigned URL TTL:** 1 hour (`signedURLExpiry = time.Hour`)
**Upload retry:** 3 attempts with exponential backoff (100ms, 200ms)
**Batch delete:** up to 1000 keys per `DeleteObjects` call
**Slide HTML source (worker):** each slide JPEG can have a sibling object `slides/{jobId}/slide_XX.html` (`Content-Type: text/html`). The Go API persists `chat_content_image.html_s3_key` only when the worker sends `htmlS3Key` on the completion callback (`HeadObject` must succeed before commit). Behaviour is configurable via **`REQUIRE_HTML_ARTIFACT_UPLOAD`** on the worker (default true): when true, missing HTML artefacts fail the job and uploaded JPEG/HTML keys from that attempt are cleaned up before the failure callback.

**Diagnosing missing HTML in S3 (operational checklist):**

1. **Postgres (`chat_content_image`)** — for a recent assistant turn, inspect `html_s3_key`. All null ⇒ the worker omitted `htmlS3Key` in the completion payload or never uploaded HTML. Non-null ⇒ the API validated the object existed at completion time (stale deletes are a separate issue).
2. **Worker logs** — search for `node=upload_assets` and HTML key paths; upload errors are logged and, when uploads fail after retries, surfaced in pipeline `errors` for observability.
3. **Deploy** — confirm the running worker image includes HTML upload logic in `upload_assets.py`.
4. **Env alignment** — same `AWS_S3_BUCKET` / region / credentials as intended; IAM must allow `s3:PutObject` on `slides/*` (JPEG and HTML share the same call).
5. **Console** — list `slides/<job_uuid>/` and expect `.html` next to `.jpeg` when uploads succeed.

---

### Integração estruturada experimental

O fluxo `structured_v1` usa snapshots `document.json`, manifesto `assets.json` e cópias de imagens em `slides/{jobId}/assets/`, com escrita condicional. A API valida ownership e artefatos antes de publicar uma versão; a reconciliação de órfãos possui agendamento desativado por padrão. A flag `STRUCTURED_POSTS_ENABLED` controla novos chats estruturados e `STRUCTURED_WORKER_URLS` lista endereços diretos de workers compatíveis. Veja detalhes e limites em `docs/RUNBOOK.md`.

## AI / LLM — Slide Generation (Worker)

**Serviço:** OpenAI no worker. `OPENAI_CHAT_MODEL` e `REFERENCE_VISION_MODEL` usam `gpt-5.4` por padrão. No fluxo legado, o grafo analisa referências e anexos, planeja e gera ou edita um pacote JSON com HTML por slide. No fluxo estruturado experimental, gera um documento tipado ou operações de edição. Os prompts ficam em `apps/worker/prompts/`; a implementação está em `apps/worker/app/nodes/` e `graph.py`.

---

## Inter-Service Communication: API → Worker

**Protocol:** HTTP/JSON
**Endpoint:** `POST {WORKER_URL}/jobs`
**Authentication:** shared `X-Worker-API-Key` header
**Payload (`DispatchPayload`):**
```json
{
  "job_id": "<uuid>",
  "user_id": "<uuid>",
  "chat_id": "<uuid>",
  "message_id": "<uuid>",
  "chat_post_type": "carousel",
  "raw_message": "...",
  "audit_text": "...",
  "brand_text": "...",
  "reference_s3_keys": ["slides/..."],
  "user_attachments": [{"id": "<uuid>", "s3_key": "users/.../current.png", "mime_type": "image/png", "sort_order": 0}],
  "known_attachments": [{"id": "<uuid>", "s3_key": "users/.../historical.png", "mime_type": "image/png", "sort_order": 0}],
  "existing_slide_html_s3_keys": ["slides/{jobId}/slide_01.html"],
  "existing_slide_html": [{"slide_number": 1, "html_s3_key": "slides/{jobId}/slide_01.html"}],
  "expects_slide_refinement": false
}
```
- `user_attachments` (optional): only images attached to the current user message; used by the worker as prompt context and potential slide requirements.
- `known_attachments` (optional): all chat attachments known to the API, including prior messages; used only to resolve stable `attachment://<id>` references when rendering/refining historical HTML.
- `existing_slide_html_s3_keys` (optional): S3 keys for HTML sources of slides from a prior assistant turn; the worker loads them for the `edit_slides` path when non-empty.
- `existing_slide_html` (optional): numbered HTML sources; preferred over the legacy key list.
- `expects_slide_refinement` (optional): when `true`, the API indicates the chat already had slide JPEGs. If no HTML sources are available, intent detection fails with `JOB_FAILURE_REFINEMENT_CONTEXT`. If sources exist, intent detection can choose a new post or an edit; an edit fails if the HTML fetch is incomplete.
**Response:** `202 {"accepted": true, "job_id": "..."}` — dispatch is fire-and-forget; worker processes in background.
**Implementation:** `apps/api/internal/jobs/worker_client.go` — `HTTPWorkerClient`
**Configuration:** `WORKER_URL` (e.g., `http://worker:8000`), `WORKER_API_KEY`
**Fallback:** if `WORKER_URL` is empty, the worker client is `nil` and PostMessage returns `503 "async generation is not configured on this server"`.

## Inter-Service Communication: Worker → API (Progress)

**Protocol:** HTTP/JSON
**Endpoint:** `POST {GO_API_URL}/internal/jobs/:id/progress`
**Authentication:** same `X-Worker-API-Key` header
**Payload:**
```json
{
  "stage": "rendering_slides",
  "progress": 88
}
```
The API stores `jobs.stage`, monotonic `jobs.progress`, and `jobs.heartbeat_at`. The public job status endpoint returns stage and progress so the SPA can show a more specific loading state and progress bar. Stuck-job cleanup uses `COALESCE(heartbeat_at, updated_at)` to avoid failing jobs that are still reporting progress.

---

## Inter-Service Communication: Worker → API (Callback)

**Protocol:** HTTP/JSON
**Endpoint:** `POST {GO_API_URL}/internal/jobs/:id/complete`
**Authentication:** same `X-Worker-API-Key` header
**Payload (`CompleteBody`):**
```json
{
  "assistantText": "Caption text shown in chat",
  "artifacts": [
    {
      "s3Key": "slides/{jobId}/slide_01.jpeg",
      "slideNumber": 1,
      "htmlS3Key": "slides/{jobId}/slide_01.html"
    }
  ],
  "error": null
}
```
(`htmlS3Key` may be omitted or null when HTML upload is skipped or failed; if `REQUIRE_HTML_ARTIFACT_UPLOAD=true` on the worker, the callback uses the error path when any slide is missing HTML.)
**On success:** API writes assistant `ChatContent`, `ChatContentImage` rows, marks `Job.status = done` — all in one DB transaction.
**On error:** API marks `Job.status = failed` with `error_msg`.
**Implementation:** `apps/api/internal/jobs/handler.go`, `complete.go`
**Configuration:** `GO_API_URL` in `apps/worker/.env`

---

## HTML → JPEG Rendering

**Service:** Playwright (headless Chromium, bundled)
**Purpose:** Convert LLM-generated HTML slide markup into pixel-perfect JPEG images.
**Implementation:** `apps/worker/app/nodes/render_and_contrast.py`
**Settings:**
- Viewport: 1080 × 1350 px (4:5 portrait, alinhado ao feed Instagram)
- Screenshot: tamanho do viewport apenas (`full_page=False`), evitando JPEG com altura errada se o HTML tiver overflow
- JPEG quality: 92
- Page load timeout: 60 000 ms (`networkidle`)
- One new browser page per slide; browser shared within the run
**Playwright install:** `playwright install chromium` baked into the worker Dockerfile

---

## PostgreSQL

**Service:** PostgreSQL 16 (Alpine)
**Purpose:** Primary data store for users, chats, messages, jobs, profiles, and references.
**Configuration:** `DATABASE_URL` env var (libpq connection string)
**Migrations:** golang-migrate v4; SQL files in `apps/api/internal/db/migrations/` numbered 001–016; applied automatically at API startup via `db.RunMigrations()`
**Connection:** GORM + pgx/v5 driver; single connection pool shared across all repositories
**Notable schema features:**
- PostgreSQL native `uuid` type with `gen_random_uuid()` default
- Custom enum types (`role_enum`, `post_type_enum`, `chat_content_role_enum`, `job_status_enum`)
- Cascading deletes via GORM constraints

---

## Docker / Docker Compose

**Purpose:** Container orchestration for local development and production.
**Services defined:**
- `postgres` — PostgreSQL 16-alpine with health check (`pg_isready`)
- `api` — Go binary; starts after postgres is healthy; health check `GET /health`
- `worker` — Python uvicorn; starts after api is healthy (60s start period); health check `curl /health`
**Networking:** bridge network `app-net`; inter-service DNS by service name (`postgres`, `api`, `worker`)
**Volumes:** named volume `pgdata` for Postgres persistence
**Production overlay:** `docker-compose.prod.yml` applied on top of base compose for prod deployments
