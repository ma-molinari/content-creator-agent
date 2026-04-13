# Content Creator Agent — Tasks

**Design**: `.specs/features/content-creator-agent/design.md`
**Arquitetura**: `docs/architecture-go-api-langgraph.md`

**Status**: Plano reescrito — construção do zero (Go API sem `internal/agent/` / `internal/export/` + projeto `worker/` Python). Tarefas antigas T1–T23 descartadas como base de continuidade; o roadmap abaixo é a fonte de verdade.

---

## Execution Plan

### Fase 1 — Go API (limpa, sem agente)

Sequencial na dependência crítica; T4–T7 podem ser desenvolvidos em paralelo após T3 conforme capacidade.

```
T1 → T2 → T3 → T4..T7 (paralelo) → T8 → T9 → T10 → T11 → T12 → T13 → T14
```

### Fase 2 — Python Worker (LangGraph) — `worker/`

Pode iniciar em paralelo com Fase 1 após T1 (estrutura de repo).

```
TP1 → TP2 → TP3 → TP4 → TP5 → TP6 → TP7 → TP8 → TP9 → TP10 → TP11
```

### Fase 3 — Integração Go ↔ Python

Após T11 + T12 + TP11.

```
TI1 → TI2 → TI3
```

### Fase 4 — Frontend (React)

Paralelo com Fase 2 após T3 (contratos estáveis o suficiente); UI com **polling** de `GET /chats/:id/jobs/:jobId/status` e estado "gerando…".

```
T3 → T24 → T25 → T26 [P] ──┐
                  T27 [P] ──┤──→ T28 → T29 → T30 → T31 → T32 → T33
```

### Fase 5 — Cron (Go)

Após T8 (chats + conteúdo).

```
T8 → T34 → T35
```

### Fase 6 — QA & Deploy

Dois containers (Go API + Python Worker), Docker Compose / ECS Task, smoke tests, observabilidade com `job_id` rastreável.

```
T36 [P] ──┐
T37 [P] ──┼──→ T38 → T39 → T40 → T41
T35 ──────┘
```

---

## Parallel Execution Map

```
Fase 1 Go API: T1 → T2 → T3 → T4..T7 (paralelo) → T8 → T9 → T10 → T11 → T12 → T13 → T14
Fase 2 Worker: TP1 → TP2 → TP3..TP9 (sequencial) → TP10 → TP11
Fase 3: após T12 + TP11 → TI1 → TI2 → TI3
Fase 4: após T3 (paralelo com Fase 2)
Fase 5: após T8
Fase 6: após Fases 3 + 4 + 5

Caminho crítico: T1→T2→T3→T8→T11→T12→TI1→TI2→TI3→Fase6
```

---

## Fase 1 — Go API (limpa, sem agente)

| Task | O que faz | Depende de |
|------|-----------|------------|
| **T1** | Setup projeto Go: Echo, estrutura `cmd/` + `internal/`, Dockerfile **sem** Playwright, `go.mod` | — |
| **T2** | Schema + migrations PostgreSQL: `users`, `chats`, `chat_content`, `chat_content_image`, `chat_content_resume`, **`jobs`** | T1 |
| **T3** | GORM + config (`DATABASE_URL`, `JWT_SECRET`, `WORKER_URL`, `WORKER_API_KEY`, `S3_*`) | T2 |
| **T4** | Auth: `POST /auth/register` — securityKey, validações, 409 | T3 |
| **T5** | Auth: `POST /auth/login` — JWT access + refresh cookie httpOnly | T3 |
| **T6** | Auth: `POST /auth/refresh` + middleware JWT; `POST /auth/recover-password` | T5 |
| **T7** | Rate limit (auth por IP, LLM/job por user), CORS, security headers | T6 |
| **T8** | CRUD chats: `GET/POST /chats`, `GET/DELETE /chats/:id`; limite 5 + remoção automática do mais antigo | T3 |
| **T9** | S3 Service: Upload, SignedURL, Delete, DeleteMany (backoff 3x) | T3 |
| **T10** | Arquivos: `GET /chats/:id/files`, `GET /chats/:id/files/:fileId`, `GET /chats/:id/files/download` (zip) | T8 + T9 |
| **T11** | `POST /chats/:id/messages` — sanitiza input, persiste mensagem do usuário, cria job, despacha `POST WORKER_URL/jobs`, retorna **`202 Accepted` + `jobId`** | T8 + T7 |
| **T12** | `POST /internal/jobs/:id/complete` — protegido por `WORKER_API_KEY`; persiste mensagem assistente + imagens; atualiza status do job | T11 |
| **T13** | `GET /chats/:id/jobs/:jobId/status` — polling: `pending` / `processing` / `done` / `failed` | T12 |
| **T14** | `GET /setup/status` — verifica perfil do usuário (AUDIT/BRAND presentes) | T3 |

---

## Fase 2 — Python Worker (LangGraph) — `worker/`

| Task | O que faz | Depende de |
|------|-----------|------------|
| **TP1** | Setup Python: `worker/pyproject.toml` (uv), FastAPI, Dockerfile (Playwright/Chromium), `.env.example` (`OPENAI_API_KEY`, `S3_*`, `GO_API_URL`, `WORKER_API_KEY`) | — |
| **TP2** | Estado LangGraph (`TypedDict`/Pydantic): `user_id`, `chat_id`, `job_id`, `raw_message`, `profile_text`, `optimized_brief`, `slides_html[]`, `s3_keys[]`, `errors[]` | TP1 |
| **TP3** | Nó `load_profile`: perfil inline no payload (AUDIT/BRAND como strings) | TP2 |
| **TP4** | Nó `optimize_prompt`: OpenAI + system prompt do otimizador (portado de `.cursor/` / skills) | TP3 |
| **TP5** | Nó `generate_slides`: OpenAI + skill de slides; saída com marcadores `###SLIDE_FILE:...###` | TP4 |
| **TP6** | Nó `parse_validate`: parser dos marcadores; validação HTML mínima; aresta condicional de retry → TP5 (máx. 2x) | TP5 |
| **TP7** | Nó `render_to_jpeg`: playwright-python headless; 768×1376px, JPEG qualidade 92 | TP6 |
| **TP8** | Nó `upload_assets`: boto3 → S3; lista `{ s3_key, slide_number }` | TP7 |
| **TP9** | Nó `finalize`: `POST {GO_API_URL}/internal/jobs/:job_id/complete` com texto + artefatos | TP8 |
| **TP10** | Montagem do grafo LangGraph: nós, arestas condicionais (retry em TP6), compilar | TP2–TP9 |
| **TP11** | `POST /jobs`: valida `WORKER_API_KEY`; dispara `graph.ainvoke` em **BackgroundTasks** (async) | TP10 |

---

## Fase 3 — Integração Go ↔ Python

| Task | O que faz |
|------|-----------|
| **TI1** | Teste de integração: Go despacha job → worker recebe e processa (mock LLM + mock S3) → callback chega ao Go |
| **TI2** | Teste E2E com LLM real: mensagem → slides → JPEGs no S3 → chat atualizado no Go |
| **TI3** | Testes de falha: worker erro → Go `failed` → frontend trata |

---

## Fase 4 — Frontend

Mesmas entregas do plano anterior (T24–T33), com **polling** de status de job e UI "gerando…" durante `pending`/`processing`.

| Task | Escopo resumido |
|------|-----------------|
| **T24** | Setup React (Vite, Zustand, React Query, Tailwind, rotas) |
| **T25** | Layout base + tema |
| **T26** | Login |
| **T27** | Cadastro + modal security key |
| **T28** | Interceptor JWT + refresh |
| **T29** | Chat: setup gate + rich text |
| **T30** | Envio mensagem: `202` + `jobId`; polling status / `GET /chats/:id` |
| **T31** | SlideViewer + downloads |
| **T32** | Histórico — lista |
| **T33** | Histórico — re-prompt, download, delete |

---

## Fase 5 — Cron (Go)

| Task | Escopo |
|------|--------|
| **T34** | Scheduler diário (ex. 02:00 UTC) |
| **T35** | Sumarização com GPT-5.4 Mini → `chat_content_resume` |

---

## Fase 6 — QA & Deploy

| Task | Escopo |
|------|--------|
| **T36** | Testes unitários backend (pacotes Go relevantes; sem exigir `internal/agent` legado) |
| **T37** | Testes integração API + DB |
| **T38** | E2E Playwright (fluxos críticos + job async) |
| **T39** | Docker Compose: API Go + worker Python + Postgres |
| **T40** | Staging + smoke tests |
| **T41** | Produção + monitoramento (`job_id` nos logs) |

---

## Granularity Check

| Bloco | Escopo |
|-------|--------|
| T1–T14 | Um incremento vertical por task na Fase 1 |
| TP1–TP11 | Pipeline Python por nós até grafo + endpoint |
| TI1–TI3 | Integração e confiabilidade do contrato |
| T24–T41 | Alinhado a entregas de UI e operações |

---

## Referência de requisitos

Mapeamento em `.specs/features/content-creator-agent/spec.md` — Requirement Traceability (incl. POST-10, POST-11).
