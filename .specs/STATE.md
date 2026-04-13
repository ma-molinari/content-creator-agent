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
| **Fase 1 — Go API limpa** | T1–T14 | **Em progresso** — núcleo async implementado (jobs, `POST /chats/:id/messages` → 202 + `jobId`, callback `POST /internal/jobs/:id/complete`, `GET .../jobs/:jobId/status`, config `WORKER_*`, `PROFILE_DATA_ROOT`); pacotes legados removidos (`internal/agent`, `internal/export`); sem `backend/promptdata/` (prompts em `.cursor/`; worker consumirá dali ou paths configuráveis). |
| **Fase 2 — Worker Python LangGraph** | TP1–TP11 | **Pendente** |
| **Fase 3 — Integração** | TI1–TI3 | **Pendente** |
| Fase 4 — Frontend | T24–T33 | Pendente |
| Fase 5 — Cron | T34–T35 | Pendente |
| Fase 6 — QA & Deploy | T36–T41 | Pendente |

**Próximo passo sugerido:** **Fase 2 — Worker Python** (`worker/`) para consumir `POST {WORKER_URL}/jobs` e concluir via `POST /internal/jobs/:id/complete` no Go; em paralelo **integração TI1–TI3** quando o worker expuser contrato estável. Ver `docs/architecture-go-api-langgraph.md` e `design.md` (contrato Go ↔ Python).

**Nota:** A spec e o `tasks.md` foram reescritos para arquitetura **Go API + worker Python**; validar tarefas T1–T14 contra o código atual e marcar itens fechados no `tasks.md` quando conveniente.

---

## Histórico de implementação (contexto futuro)

Entradas cronológicas do que foi efetivamente construído em código frente à spec. *Atualizar ao fechar fases.*

### 2026-04-13 — Go API (Fase 1, núcleo)

**Implementado no backend:** modelo e migration `jobs`; `POST /chats/:id/messages` assíncrono (persistência mensagem + job, dispatch HTTP ao worker, status `processing` / `failed`); `POST /internal/jobs/:id/complete` (API key `X-Worker-API-Key`); `GET /chats/:id/jobs/:jobId/status`; `GET /setup/status` sem `ProfileChecker` do agente; cliente HTTP `WORKER_URL` + `WORKER_API_KEY`; Dockerfile da API sem Playwright/Chromium.

**Removido do repo:** `internal/agent/`, `internal/export/`, `backend/promptdata/`, `scripts/sync-promptdata.sh`, alvo `make prompts-sync`. Dependência `langchaingo` retirada do `go.mod`.

**README:** prompts documentados como vivendo em `.cursor/` para o worker.

### 2026-04-12 — Reescrita da spec (Go API + LangGraph)

**Objetivo:** Documentar dois serviços — API Go (CRUD, auth, jobs, callback) **sem** `internal/agent/` / `internal/export/` no desenho alvo; processamento em **`worker/`** (Python, LangGraph, Playwright, S3). Contrato: `POST /chats/:id/messages` → `202` + `jobId`; `POST /internal/jobs/:id/complete` no Go.

**Documentação atualizada:** `spec.md`, `design.md`, `tasks.md` (reescrito), `STATE.md`, `docs/PRD.md`, `docs/TDD.md`.

---

## Trabalho em progresso

| Feature | Marco | Notas |
|---------|--------|-------|
| content-creator-agent | Fase 1 Go (fecho) | Revisar T1–T14 vs código; frontend e cron ainda não cobertos pelas fases 4–5. |
| content-creator-agent | Fase 2 Worker | Diretório `worker/` e pipeline LangGraph ainda por implementar. |

## Decisões registradas

| # | Decisão | Contexto | Data |
|---|---------|----------|------|
| 1 | Limite de 5 chats: remoção automática do mais antigo ao criar o 6º | Usuário pode deletar manualmente qualquer chat | 2026-04-10 |
| 2 | Redis: rate limiting em memória no V1 (Redis opcional) | Redis pode ser adotado para escala horizontal no V2 | 2026-04-10 |
| 3 | JWT: refresh token em cookie httpOnly + Secure + SameSite=Strict; access token em memória no cliente | Nunca em localStorage para proteção XSS | 2026-04-10 |
| 4 | Geração de slides: GPT-5.4 Mini → HTML/CSS → Playwright → JPEG (768×1376px, qualidade 92) | Sem modelo dedicado de geração de imagem | 2026-04-10 |
| 5 | Limite de 4.000 tokens de saída por requisição ao LLM | Estimativa conservadora; revisar com dados reais de produção | 2026-04-10 |
| 6 | Cookie `Secure` em `COOKIE_SECURE` (default true em produção; `false` para HTTP local) | Permite testar login/refresh em dev sem HTTPS | 2026-04-12 |
| 7 | System prompts: canónico em `.cursor/` skills/rules; **sem** cópia `backend/promptdata/` — worker lê `.cursor/` ou paths configuráveis | Evita duplicar sync para o Go | 2026-04-13 |
| 8 | **Arquitetura do zero: Go = API/CRUD/jobs (sem agent/export no desenho alvo); Python + LangGraph = motor em `worker/`.** | **`docs/architecture-go-api-langgraph.md`** | **2026-04-12** |

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

## Contexto de sessão (referência rápida)

- **TDD:** `docs/TDD.md`
- **Stack alvo:** Go/Echo (API) + React + PostgreSQL + S3 + **Python (LangGraph, FastAPI, Playwright, boto3)** no `worker/`
- **Contrato:** ver `design.md` — seção **Contrato Go ↔ Python**
