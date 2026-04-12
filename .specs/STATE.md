# Estado da Sessão — Content Creator Agent

## Última atualização

2026-04-12

## Feature em foco

| Item | Valor |
|------|--------|
| Spec | `.specs/features/content-creator-agent/spec.md` |
| Design | `.specs/features/content-creator-agent/design.md` |
| Tasks | `.specs/features/content-creator-agent/tasks.md` |
| TDD | `docs/TDD.md` |

## Status vs plano de tasks

| Fase | Escopo (tasks.md) | Estado |
|------|-------------------|--------|
| **Fase 1 — Base** | T1–T8 (backend foundation) | **Concluída** — ver histórico abaixo |
| **Fase 2 — Core API** | T9–T17 | **Concluída** — ver histórico abaixo |
| **Fase 3 — Agent + Export** | T18–T23 | **Concluída** — ver histórico abaixo |
| Fase 4 — Frontend | T24–T33 | Pendente |
| Fase 5 — Cron | T34–T35 | Pendente |
| Fase 6 — QA & Deploy | T36–T41 | Pendente |

**Próximo passo sugerido:** iniciar Fase 4 (T24 em diante — frontend React), com backend já expondo `POST /chats/:id/messages`, `GET /setup/status` e variáveis `OPENAI_API_KEY`, `PROFILE_DATA_ROOT`, `REPO_ROOT` configuradas para testes integrados.

---

## Histórico de implementação (contexto futuro)

Entradas cronológicas do que foi efetivamente construído em código frente à spec. *Atualizar este bloco quando fechar fases ou marcos relevantes.*

### 2026-04-12 — Fase 3 (T18–T23) entregue

**Objetivo da spec:** pipeline LLM (Langchain Go) com otimização de prompt, geração de slides HTML/CSS a partir de `AUDIT.md` / `BRAND.md` por usuário, export JPEG via Playwright (`scripts/export-slides.js`), upload S3 e persistência de mensagens; verificação de setup e endpoint de status.

**Implementado em `backend/`:**

- **T18:** `internal/agent/llm.go` — cliente OpenAI via `tmc/langchaingo`, modelo padrão `gpt-5.4-mini`, `max_tokens` 4000, timeout 60s por tentativa, até 3 tentativas com backoff; teste com mock HTTP (`TestLLMClient_MockOpenAI`).
- **T19:** `internal/agent/prompt_optimizer.go` — `OptimizePrompt`, sanitização (HTML + controles), regras anti–injection; testes de sanitização e estrutura do system prompt.
- **T20:** `internal/agent/slide_generator.go` — `GenerateSlides`, delimitador `###SLIDE_FILE:...###`, leitura de perfil via `ProfileChecker`; erro `SETUP_REQUIRED` antes do LLM se faltar arquivo.
- **T21:** `internal/export/playwright_runner.go` — `ExportJPEGs(ctx, carouselDir)` com `node scripts/export-slides.js --export --confirm`, stderr logado, `REPO_ROOT` obrigatório, timeout configurável (`EXPORT_TIMEOUT`, padrão 120s).
- **T22:** `internal/chat/post_message.go` — orquestração optimize → slides → temp dir → export → S3 → `CreateContentWithImages`; reprompt via `chat_content_resume.summary` ou histórico; `POST /chats/:id/messages` com grupo `LLMByUser` (10/min); resposta com `message` + `files[]`.
- **T23:** `internal/agent/profile_checker.go` — `CheckProfileSetup` / `LoadProfileText` em `PROFILE_DATA_ROOT/instagram-audits/<user_uuid>/`; `GET /setup/status` → `{ "configured": bool }`.
- **Config:** `OPENAI_API_KEY`, `OPENAI_MODEL`, `PROFILE_DATA_ROOT`, `REPO_ROOT`, `EXPORT_TIMEOUT` em `internal/config/config.go` e `backend/.env.example`.

**Verificação:** `go test ./internal/agent/...`, `go test ./internal/export/...`, `go test ./internal/chat/...`.

---

### 2026-04-12 — Fase 2 (T9–T17) entregue

**Objetivo da spec:** Core API de chats (CRUD), serviço S3 (upload com retry, signed URL, delete em lote, download de objeto), limite de 5 chats com remoção do mais antigo, endpoints de arquivos (lista com URL assinada 1h, zip em memória, JPEG por id).

**Implementado em `backend/`:**

- **T13:** `internal/storage/s3.go` — interface `StorageService` com `Upload`, `GetSignedURL`, `GetObject`, `Delete`, `DeleteMany`; AWS SDK v2; upload com backoff 3 tentativas; `internal/storage/s3_test.go` (caso mínimo).
- **T9–T12, T15–T17:** `internal/chat/repository.go`, `service.go`, `handler.go` — rotas protegidas por JWT: `GET/POST /chats`, `GET/DELETE /chats/:id`, `GET /chats/:id/files`, `GET /chats/:id/files/download`, `GET /chats/:id/files/:fileId`. Associações GORM em `internal/db/models.go` (`Chat.Contents`, `ChatContent.Images`, `Chat.Resume`).
- **T14:** `CreateChat` conta chats; com ≥5 remove o mais antigo via mesmo fluxo de delete (S3 + cascade DB); testes `TestChatLimit_*` em `internal/chat/service_test.go` (SQLite in-memory).
- **Bootstrap:** `cmd/server/main.go` exige `AWS_REGION` e `AWS_S3_BUCKET` (e credenciais via env ou IAM); placeholder `internal/s3/` removido em favor de `internal/storage/`.

**Verificação:** `go test ./...`, `go vet ./...`.

---

### 2026-04-12 — Fase 1 (T1–T8) entregue

**Objetivo da spec:** base do backend (Echo, PostgreSQL, migrations, GORM, auth JWT, rate limit, headers, Docker com Playwright/Chromium para fase futura de export).

**Implementado em `backend/`:**

- **T1:** `go.mod`, `cmd/server/main.go`, `Dockerfile` multi-stage (Go + Node/Playwright + `chromium`), pacote `internal/chat` como placeholder (S3 evoluiu para `internal/storage/` na Fase 2).
- **T2:** Migrations SQL versionadas em `internal/db/migrations/` (`001`–`006`, up/down): enums (`post_type_enum`, `role_enum`, `chat_content_role_enum`), tabelas `users`, `chats`, `chat_content`, `chat_content_image` (`s3_key`, `url`, `slide_number`), `chat_content_resume`.
- **T3:** `internal/db/db.go` (`Connect` com panic se `DATABASE_URL` ausente), `models.go`, runner de migrations com `embed` + `golang-migrate`, testes em `internal/db/db_test.go`, `backend/.env.example`.
- **T4:** `POST /auth/register` — body `{ email, password }`, resposta `{ securityKey }` (UUID em texto claro uma vez); 409 email duplicado; 400 validação básica (senha ≥ 8 caracteres).
- **T5:** `POST /auth/login` — `{ accessToken }` no JSON; refresh token em cookie `refresh_token` (`httpOnly`, `SameSite=Strict`, `Secure` configurável via `COOKIE_SECURE`).
- **T6:** `POST /auth/refresh` lê o cookie de refresh; middleware JWT em `internal/middleware/jwt.go` (`Authorization: Bearer`); rotas protegidas de exemplo: `GET /me`, `GET /api/llm/ready` (JWT + rate limit LLM).
- **T7:** `POST /auth/recover-password` — fluxo email + `securityKey` + `newPassword` com códigos 404/403 conforme spec de segurança.
- **T8:** Rate limit in-memory: `/auth/*` por IP (20 req / 5 min); prefixo `/api/llm/*` por `user_id` (10 req / min, placeholder até existirem rotas LLM reais); headers `X-Content-Type-Options`, `X-Frame-Options`; CORS por allowlist `CORS_ALLOWED_ORIGINS`.

**Verificação:** `go build ./cmd/server`, `go test ./internal/db/...`; imagem Docker `content-creator-agent-backend` construída com sucesso (inclui download do Chromium via Playwright).

**Nota de alinhamento com `docs/TDD.md`:** o TDD menciona `refreshToken` no body em alguns trechos; a implementação segue a decisão já registrada (decisão #3 abaixo): refresh só em cookie, não em `localStorage`/body de login.

---

## Trabalho em progresso

| Feature | Marco | Notas |
|---------|--------|--------|
| content-creator-agent | Fase 3 fechada | Agente + export + POST mensagens + setup status; próximo: Fase 4 (frontend) |

## Decisões registradas

| # | Decisão | Contexto | Data |
|---|---------|----------|------|
| 1 | Limite de 5 chats: remoção automática do mais antigo ao criar o 6º | Usuário pode deletar manualmente qualquer chat | 2026-04-10 |
| 2 | Redis: rate limiting em memória no V1 (Redis opcional) | Redis pode ser adotado para escala horizontal no V2 | 2026-04-10 |
| 3 | JWT: refresh token em cookie httpOnly + Secure + SameSite=Strict; access token em memória no cliente | Nunca em localStorage para proteção XSS | 2026-04-10 |
| 4 | Geração de slides: GPT-5.4 Mini → HTML/CSS → export-slides.js (Playwright/Chromium) → JPEG (768×1376px, qualidade 92) | Sem modelo dedicado de geração de imagem | 2026-04-10 |
| 5 | Limite de 4.000 tokens de saída por requisição ao LLM | Estimativa conservadora; revisar com dados reais de produção | 2026-04-10 |
| 6 | Cookie `Secure` em `COOKIE_SECURE` (default true em produção; `false` para HTTP local) | Permite testar login/refresh em dev sem HTTPS | 2026-04-12 |

## Bloqueadores ativos

Nenhum.

## Ideias adiadas (deferred)

| Ideia | Motivo do adiamento | Fase alvo |
|-------|---------------------|-----------|
| Tela de configuração de perfil (upload de referências visuais) | Fora do escopo V1 | V2 |
| Publicação direta no Instagram via API | Fora do escopo V1 | V2 |
| Redis para rate limiting e cache de sessões | Opcional no V1, adotado se escala horizontal necessária | V2 |
| Histórico expandido (mais de 5 posts) | Fora do escopo V1 | V2 |
| Expansão para outros formatos (Reels, Stories) | Fora do escopo V1 | V2 |
| Cloudflare R2 como alternativa ao S3 | Alternativa viável, custo de egress menor | V2 |

## Lições aprendidas

| Data | Lição |
|------|--------|
| 2026-04-12 | Build Docker do backend validado: estágio final inclui Playwright + Chromium (~100 MiB download na build) — tempo de CI/deploy a considerar. |

## Contexto de sessão (referência rápida)

- **TDD de referência**: `docs/TDD.md` — arquitetura, modelo de dados, APIs, segurança e plano de implementação.
- **Stack decidida**: Golang/Echo (backend) + React (frontend) + PostgreSQL + Amazon S3 + Langchain + OpenAI GPT-5.4 Mini.
- **Código backend atual**: `backend/` — entrypoint `cmd/server/main.go`.
- **Agent/export (V1):** `OPENAI_API_KEY`, `PROFILE_DATA_ROOT` (`instagram-audits/<user_uuid>/AUDIT.md` + `BRAND.md`), `REPO_ROOT` (raiz do repo com `scripts/export-slides.js`); rotas `POST /chats/:id/messages`, `GET /setup/status`.
- **Skills existentes a reutilizar**: `create-social-post`, `map-instagram-profile`, `prompt-engineering-meta`, `export-slides.js`.
- **Abordagem de geração de imagens**: HTML/CSS via LLM → Playwright/Chromium → JPEG (sem DALL-E).
