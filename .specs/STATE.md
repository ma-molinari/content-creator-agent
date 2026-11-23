# Estado da Sessão — Post Mind

## Planejamento: fidelidade visual — 2026-11-23

- **Status:** T01 aprovada pelo responsável; T02–T04 validadas em 23/11/2026; implementação das demais tarefas pendente.
- **Design:** `docs/TDD-FIDELIDADE-VISUAL.md`; **tarefas:** `.specs/features/visual-fidelity/tasks.md`.
- **Decisão do usuário:** permitir aplicar os novos elementos em posts híbridos V1 e salvar uma nova versão V2, preservando a V1.
- **Gates:** catálogo de barras/linhas e política de contraste aprovados conforme `.specs/features/visual-fidelity/catalogo-v2-proposta.md`; a T18 híbrida e o aceite operacional permanecem pré-requisitos para ativação, não para desenvolvimento isolado.

## Planejamento: geração híbrida — 2026-11-18

- **Status:** T01, T02 e T03 concluídas: catálogo inicial V1 aprovado pelo responsável em 2026-11-18, com testes de renderização em Chromium; T04 e T06 implementadas sobre o catálogo V1; T05 concluída com teste entre serviços para edição não suportada; T07 concluída: cópia e releitura de assets herdados validadas entre serviços, inclusive após exclusão da referência original; T08 e T09 concluídas e validadas em PostgreSQL temporário; T15 concluída no catálogo V1, com interface, leitura de versão e testes integrados; T11 concluída e T16 concluída em ambiente simulado: inventário durável e varredura com agendamento desativado, recuperação validada em processo separado com armazenamento local; consultas ao banco e listagem S3 paginadas; recuperação e custo relativo validados em Docker com S3 simulado, com consultas e exclusões agrupadas; inventários retidos indefinidamente, com validação em S3 real pendente; T12 e T13 concluídas no catálogo V1: caminho estruturado conectado, com teste entre API HTTP e worker HTTP, Chromium real e LLM/S3 simulados; reconciliação operacional continua pendente na T16; T10 concluída no catálogo V1, com validação de snapshot/manifesto, contratos compartilhados e testes de concorrência; T14 e T17 concluídas localmente: integração, flag, negociação e agregação dos logs validadas; T18 tem ensaio Docker reproduzível, mas a aceitação com serviços reais continua pendente.
- **Requisitos:** `.specs/features/hybrid-post-generation/spec.md`; **tarefas:** `.specs/features/hybrid-post-generation/tasks.md`; **design:** `docs/TDD-MODELO-HIBRIDO.md`.
- **Decisões do usuário:** templates flexíveis, edição linear da versão corrente com rejeição de conflitos; catálogo inicial V1 aprovado pelas amostras; responsável é o usuário, sem ticket.
- **Divergência preexistente resolvida:** o teste de acesso a chat de outro usuário foi alinhado ao HTTP 403 já implementado e documentado; a suíte de integração completa passou com PostgreSQL temporário.
- **Pendências:** configuração operacional dos destinos, coleta de métricas, reconciliação com S3 real e metas de rollout. Callback incerto e rollback isolado validados com S3 e LLM reais; interrupção e proteção de referências incorporadas à reconciliação preparada no volume `postmind-t18-real-s3_pgdata`, elegível após 2026-11-23 19:45:29 UTC; executar `python tests/docker_hybrid/real_s3.py verify`. Evidências locais e limites em `.specs/features/hybrid-post-generation/validacao.md`. Preservar o histórico abaixo como registro de outras features; seu conteúdo descreve estados históricos e pode estar desatualizado em relação ao código.

## Última atualização

2026-05-05

## Feature em foco

| Item | Valor |
|------|--------|
| Feature | `attach-image-to-prompt` |
| Spec | `.specs/features/attach-image-to-prompt/spec.md` |
| Context | `.specs/features/attach-image-to-prompt/context.md` |
| Design | `.specs/features/attach-image-to-prompt/design.md` |
| Tasks | `.specs/features/attach-image-to-prompt/tasks.md` |

### Feature anterior (em execução)

| Item | Valor |
|------|--------|
| Feature | `iterative-slide-refinement` |
| Spec | `.specs/features/iterative-slide-refinement/spec.md` |
| Context | `.specs/features/iterative-slide-refinement/context.md` |
| Design | `.specs/features/iterative-slide-refinement/design.md` |
| Tasks | `.specs/features/iterative-slide-refinement/tasks.md` |
| Status | Spec + design + tasks aprovados; T13 com checkboxes parciais; demais T1–T12, T14–T15 pendentes de verificação. |

### Feature mais antiga (concluída)

| Item | Valor |
|------|--------|
| Spec | `.specs/features/content-creator-agent/spec.md` |
| Design | `.specs/features/content-creator-agent/design.md` |
| Tasks | `.specs/features/content-creator-agent/tasks.md` |

## Status vs plano de tasks

| Fase | Escopo (tasks.md) | Estado |
|------|-------------------|--------|
| **Fase 1 — Go API limpa** | T1–T14 | **Concluída (código)** — `apps/api/`: Echo, auth (JWT + refresh httpOnly), rate limit, CRUD chats (limite 5 + eviction), S3, arquivos/zip, jobs async (`POST /chats/:id/messages` → 202 + `jobId`), callback interno, polling de status, `GET /setup/status`. **Ressalvas vs tasks.md:** (1) **T9** — `Upload` tem backoff 3×; **`DeleteMany` não** (apenas batch DeleteObjects). (2) Nomes de env: código usa `AWS_REGION` / `AWS_S3_BUCKET` / etc.; o `tasks.md` menciona `S3_*` no texto — equivalente, só nomenclatura. |
| **Fase 2 — Worker Python LangGraph** | TP1–TP11 | **Concluída (código)** — `apps/worker/`: FastAPI (`POST /jobs`, `GET /health`), LangGraph (load_profile → optimize → generate_slides → parse_validate com retry → render_to_jpeg → upload_assets → finalize), prompts em `apps/worker/prompts/`, Dockerfile + Playwright Chromium, `pyproject.toml` + `.env.example`. **Ressalva:** **TP6** no `tasks.md` fala em retry máximo **2×** para `generate_slides`; o nó `parse_validate` incrementa `retry_count` enquanto `< 3` (pode haver **até 4** execuções de `generate_slides` no pior caso). Ajustar código ou spec se quiser aderência literal. |
| **Fase 3 — Integração** | TI1–TI3 | **Concluída (código + testes)** — `docker-compose.yml` na raiz (postgres + api + worker, healthchecks, `WORKER_*` / `GO_API_URL`; sem volume de perfil em disco). **TI1** — `go test -tags=integration` em `apps/api/integration/` (`INTEGRATION_DATABASE_URL`); mock worker + callback; perfil de teste via `PUT /profile`; `make test-integration` em `apps/api/Makefile`. **TI2** — `pytest` + `httpx` em `tests/e2e/`; `make e2e` no Makefile da raiz. **TI3** — `apps/api/integration/failure_test.go` (callback erro → `failed`, dispatch 500 → 502 + job `failed`, callback sem `assistantText` → 400). Tratamento de `failed` no cliente implementado na Fase 4 (T30 — `ChatThread` + `JobStatusIndicator`). |
| **Fase 4 — Frontend** | T24–T33 | **Concluída (código)** — `apps/web/`: T25 (tokens + AppShell + SidebarRail + drawer mobile `< 768px`), T26 (Login form + POST /auth/login + returnTo), T27 (Register + SecurityKeyModal), T28 (interceptor 401 → POST /auth/refresh → retry → clear + redirect), T29 (Chat: `GET /setup/status` gate + ComposerBar + `POST /chats`), T30 (`POST /chats/:id/messages` + polling 1500ms + estados pending/done/failed + retry), T31 (SlideViewer grid+lightbox+a11y + DownloadButton), T32 (History: `GET /chats` + ChatList + empty state), T33 (re-prompt, download ZIP, delete com AlertDialog, toasts). Módulos API em `src/api/auth.ts` + `src/api/chats.ts`. Toast em `src/lib/toast.ts`. Build prod: 0 erros TypeScript. |
| **Fase 5 — Cron** | T34–T35 | **Concluída (código)** — `apps/api/`: `github.com/robfig/cron/v3` (UTC), job registrado só se `OPENAI_API_KEY` estiver definida; `SUMMARIZE_CRON` (default `0 2 * * *`). Pacotes `internal/cron` (scheduler), `internal/summarizer` (repo: elegibilidade SQL + upsert `chat_content_resume`, cliente `go-openai` **gpt-5.4-mini**, `Run` com timeout 5 min + logs). `cmd/server`: Echo em goroutine; SIGINT/SIGTERM → `scheduler.Stop()` → `Shutdown`. Env documentados em `apps/api/.env.example`. |
| **Fase 6 — QA & Deploy** | T36–T41 | **Concluída (código)** — **T36:** testes unitários Go em `apps/api/` — `internal/auth/service_test.go`, `internal/jobs/repository_test.go`, `internal/summarizer/service_test.go` (interfaces `SummarizerRepository` / `SummarizerClient` em `summarizer/service.go`), `internal/config/config_test.go` (`SUMMARIZE_CRON` default). **T37:** `integration/auth_test.go`, `chat_crud_test.go`, `security_test.go`; `helpers_test.go` com `newTestEnvWithCORS` para CORS. **T38:** Playwright em `apps/web/e2e/` — `auth.spec.ts`, `chat.spec.ts`, `history.spec.ts` (API mockada via `page.route('**/api/**')`). **T39:** `docker-compose.prod.yml` (restart, `COOKIE_SECURE` / `OPENAI_API_KEY` / `SUMMARIZE_CRON`, sem volume de perfil em disco); `Makefile` — `prod-up` / `prod-down`. **T40:** `.github/workflows/ci.yml` — jobs `unit`, `integration` (Postgres service), `playwright`; job `e2e-compose` com `if: false` até segredos LLM/S3 no repo. **T41:** logs `job_id` em `jobs/handler.go`, `chat/post_message.go`, nós `apps/worker/app/nodes/*.py`; `docs/RUNBOOK.md`; nota de CI em `apps/api/.env.example`. **Ressalvas:** integração Go precisa de Postgres acessível em `INTEGRATION_DATABASE_URL` (compose base não expõe Postgres no host; CI usa serviço). E2E Python (`make e2e`) continua a exigir credenciais reais no stack. |

**Próximo passo sugerido:** habilitar o job `e2e-compose` no CI quando `OPENAI_API_KEY` e AWS estiverem nos segredos do repositório; opcional: expor Postgres no host para `make test-integration` local ou usar apenas CI. Manter `tasks.md` / checkboxes alinhados se desejar rastreio formal.

**Nota:** Monorepo: API Go em **`apps/api/`**, frontend em **`apps/web/`**, worker em **`apps/worker/`** (não `backend/` nem `worker/` na raiz). Opcional: marcar checkboxes no `tasks.md` ou alinhar T9/TP6 ao texto da spec.

---

## Histórico de implementação (contexto futuro)

Entradas cronológicas do que foi efetivamente construído em código frente à spec. *Atualizar ao fechar fases.*

### 2026-04-13 — Go API (Fase 1, núcleo)

**Implementado em `apps/api/`:** modelo e migration `jobs`; `POST /chats/:id/messages` assíncrono (persistência mensagem + job, dispatch HTTP ao worker, status `processing` / `failed`); `POST /internal/jobs/:id/complete` (API key `X-Worker-API-Key`); `GET /chats/:id/jobs/:jobId/status`; `GET /setup/status`; cliente HTTP `WORKER_URL` + `WORKER_API_KEY`; `apps/api/Dockerfile` sem Playwright/Chromium.

**Removido do repo (legado):** `internal/agent/`, `internal/export/`, `backend/promptdata/`, `scripts/sync-promptdata.sh`, alvo `make prompts-sync`. Dependência `langchaingo` retirada do `go.mod`.

**README:** prompts documentados como vivendo em `.cursor/` para referência; runtime do worker usa `apps/worker/prompts/`.

### 2026-04-13 — Worker Python (Fase 2, TP1–TP11)

**Implementado em `apps/worker/`:** projeto instalável (`pyproject.toml`, Hatchling), `Dockerfile` (Python 3.12-slim, `uv`, Playwright + Chromium), `.env.example`. Pipeline LangGraph: `load_profile` → `optimize_prompt` (modelo de chat configurável via env, default **gpt-5.4-mini** + `prompts/optimize_prompt.md`) → `generate_slides` (`prompts/generate_slides.md`) → `parse_validate` (marcadores `###SLIDE_FILE:` / `###END_SLIDE###`, retries condicionais) → `render_to_jpeg` (1080×1350, JPEG q=92) → `upload_assets` (boto3 S3, **put_object** com até 3 tentativas e backoff) → `finalize` (`httpx` → `POST {GO_API_URL}/internal/jobs/{id}/complete`). FastAPI: `POST /jobs` (202 + `BackgroundTasks` + `graph.ainvoke`), `GET /health`, validação `X-Worker-API-Key`.

**Prompts:** conteúdo operacional em `apps/worker/prompts/*.md` (derivado das regras em `.cursor/`); não há leitura direta de `.cursor/` em runtime na imagem.

### 2026-04-13 — Integração Go ↔ Python (Fase 3, TI1–TI3)

**Infra:** `docker-compose.yml` (Postgres 16, API Go, worker Python) com healthchecks, `WORKER_API_KEY` compartilhada, `GO_API_URL=http://api:8080`, `WORKER_URL=http://worker:8000` (perfil só em BD via `PUT /profile`). Imagem da API com `wget` para healthcheck.

**TI1:** `apps/api/integration/` — `go test -tags=integration` (Postgres via `INTEGRATION_DATABASE_URL`), mock worker HTTP que valida `X-Worker-API-Key` e payload `DispatchPayload`, callback assíncrono para o Echo em teste; storage mock para `GetSignedURL`; `testdata/AUDIT.md` + `BRAND.md`; alvo `make test-integration` em `apps/api/Makefile`.

**TI2:** `tests/e2e/` — `pytest` + `httpx`, `E2E_API_URL` (default `http://localhost:8080`), fixture grava perfil com `PUT /profile` (textos lidos de `tests/e2e/testdata/*.md`); `make e2e` no Makefile da raiz (compose up → pytest → down). Requer credenciais reais (`OPENAI_API_KEY`, AWS/S3) no ambiente ao rodar o stack.

**TI3:** `apps/api/integration/failure_test.go` — erro no callback (`failed` + mensagem), worker retorna 500 no dispatch (502 + job `failed` no DB), callback `{}` sem `assistantText` → 400 no endpoint interno. Tratamento no **frontend** para `failed` fica na Fase 4.

### 2026-04-13 — Frontend React (Fase 4 completa — T24–T33)

**Implementado em `apps/web/src/`:** módulos de API (`api/auth.ts`, `api/chats.ts`) com tipos completos; interceptor de response 401 → `POST /auth/refresh` → retry → clear + `window.location.replace('/login')`; Login form (email, senha, toggle visibilidade, validação client-side, returnTo, erro 401 → mensagem localizada); Register form + `SecurityKeyModal` (clipboard API, checkbox obrigatório, redirect para /login); `AppShell` com drawer mobile (< 768px) + botão hamburguer; `SidebarRail` com prop `onClose` para fechar drawer; `ComposerBar` (auto-resize, contador de caracteres, Enter para enviar, Shift+Enter para quebra); `EmptyChatState` com PromptChips; `Chat.tsx` com: `GET /setup/status` gate + banner de aviso, criação inline de chat (`POST /chats`), envio de mensagem (`POST /chats/:id/messages`), polling de job (`GET /chats/:id/jobs/:jobId/status`) com `refetchInterval` adaptativo, estados pending/processing/done/failed, retry, cabeçalho com download ZIP e delete; `ChatThread` com scroll automático + mensagens otimistas; `MessageBubbleUser` e `MessageAssistant` (com `useFiles` para URLs frescos); `JobStatusIndicator` (spinner + label); `SlideViewer` (grid horizontal de thumbnails, lightbox com prev/next + esc + contador, a11y); `DownloadButton`; `History.tsx` (lista ordenada, label de postType, data PT-BR, delete com `AlertDialog`, download ZIP); sistema de toast (`lib/toast.ts` + `ToastContainer`) montado em `App.tsx`. Build prod: 0 erros TypeScript, 151 módulos.

### 2026-04-13 — Cron e sumarização (Fase 5 — T34–T35)

**Implementado em `apps/api/`:** dependências `github.com/robfig/cron/v3` e `github.com/sashabaranov/go-openai`. Config: `OPENAI_API_KEY`, `SUMMARIZE_CRON` (default `0 2 * * *`, UTC). `internal/cron/scheduler.go` — wrapper com `Start`/`Stop`. `internal/summarizer/` — `repository.go` (chats elegíveis via `chat_content` + `chat_content_resume`, conteúdo ordenado, upsert em `chat_id`), `openai.go` (completions **gpt-5.4-mini**), `service.go` (`Run` com `context.WithTimeout` 5 min, erro por chat isolado, logs `[summarizer]` / `[WARN]` se exceder budget). `cmd/server/main.go` — job só se `OPENAI_API_KEY` ≠ ""; shutdown gracioso (signal → `scheduler.Stop()` → `Echo.Shutdown`). `.env.example` atualizado.

### 2026-04-13 — QA & Deploy (Fase 6 — T36–T41)

**Testes Go:** novos `*_test.go` em `internal/auth`, `internal/jobs`, `internal/summarizer`, `internal/config`; integração ampliada em `apps/api/integration/` (auth, CRUD chat + eviction, segurança + CORS). **Frontend:** E2E Playwright com rotas mockadas (`e2e/auth.spec.ts`, `e2e/chat.spec.ts`, `e2e/history.spec.ts`). **Deploy:** `docker-compose.prod.yml` + alvos `prod-up` / `prod-down` no Makefile da raiz (sem volume de perfil em disco). **CI:** `.github/workflows/ci.yml` (unit + integration + playwright; E2E compose desligado por padrão). **Operação:** `docs/RUNBOOK.md`; correlação de logs por `job_id` na API e no worker (nós LangGraph). **Nota E2E:** em `/login`, preencher senha com `#password` (evita colisão de `getByLabel('Senha')` com o botão “Mostrar senha”); em `/history`, navegar pelo link da sidebar (evita perder token em memória com `page.goto` full reload).

### 2026-04-12 — Reescrita da spec (Go API + LangGraph)

**Objetivo:** Documentar dois serviços — API Go (CRUD, auth, jobs, callback) **sem** `internal/agent/` / `internal/export/` no desenho alvo; processamento em **`apps/worker/`** (Python, LangGraph, Playwright, S3). Contrato: `POST /chats/:id/messages` → `202` + `jobId`; `POST /internal/jobs/:id/complete` no Go.

**Documentação atualizada:** `spec.md`, `design.md`, `tasks.md` (reescrito), `STATE.md`, `docs/PRD.md`, `docs/TDD.md`.

---

## Trabalho em progresso

| Feature | Marco | Notas |
|---------|--------|-------|
| attach-image-to-prompt | Tasks aprovadas | Spec + context + design + tasks (26 tasks, 5 fases). Pronto para Execute. Próximo passo: T1 (migration 013). |
| iterative-slide-refinement | Tasks concluídas | Spec + context + design + tasks aprovados. Pronto para Execute. |
| content-creator-agent | Pós–Fase 6 | Fases 1–6 concluídas. Opcional: ativar E2E compose no CI, fechar gaps T9/TP6. |

## Decisões registradas

| # | Decisão | Contexto | Data |
|---|---------|----------|------|
| 1 | Limite de 5 chats: remoção automática do mais antigo ao criar o 6º | Usuário pode deletar manualmente qualquer chat | 2026-04-10 |
| 2 | Redis: rate limiting em memória no V1 (Redis opcional) | Redis pode ser adotado para escala horizontal no V2 | 2026-04-10 |
| 3 | JWT: refresh token em cookie httpOnly + Secure + SameSite=Strict; access token em memória no cliente | Nunca em localStorage para proteção XSS | 2026-04-10 |
| 4 | Geração de slides: GPT-5.4 Mini → HTML/CSS → Playwright → JPEG (1080×1350px, 4:5, qualidade 92) | Sem modelo dedicado de geração de imagem | 2026-04-10 |
| 5 | Limite de 4.000 tokens de saída por requisição ao LLM | Estimativa conservadora; revisar com dados reais de produção | 2026-04-10 |
| 6 | Cookie `Secure` em `COOKIE_SECURE` (default true em produção; `false` para HTTP local) | Permite testar login/refresh em dev sem HTTPS | 2026-04-12 |
| 7 | System prompts: referência em `.cursor/` skills/rules; **sem** `backend/promptdata/` — o worker em runtime lê **`apps/worker/prompts/*.md`** na imagem (alinhar mudanças de skills com essa pasta) | Evita duplicar sync para o Go | 2026-04-13 |
| 8 | **Arquitetura do zero: Go = API/CRUD/jobs em `apps/api/` (sem agent/export no desenho alvo); Python + LangGraph = motor em `apps/worker/`.** | **`docs/architecture-go-api-langgraph.md`** | **2026-04-12** |

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
| 2026-04-13 | Prompts de execução do worker ficam em `apps/worker/prompts/` na imagem; alinhar alterações em `.cursor/rules` com cópias/atualizações nessa pasta quando necessário. |
| 2026-04-13 | Integração: testes Go com tag `integration` exigem Postgres acessível (`INTEGRATION_DATABASE_URL`); E2E com compose exige credenciais LLM/S3 no host — sem isso o worker só sobe healthy; o fluxo completo falha no job. |
| 2026-04-14 | Frontend (Fase 4): imagens dos slides em `GET /chats/:id` têm URLs presignadas que expiram em 1h (geradas no callback do job); para exibir slides sempre com URLs frescos usar `GET /chats/:id/files`. Polling de job status deve usar `staleTime: 0` e `refetchInterval` adaptativo que retorna `false` ao atingir `done`/`failed`. |
| 2026-04-13 | Cron de sumarização não roda sem `OPENAI_API_KEY` (evita falhas silenciosas em dev); expressões cron são em **UTC** — alinhar `SUMMARIZE_CRON` ao fuso desejado ou documentar para operação. |
| 2026-04-13 | Fase 6: Playwright com API mockada cobre fluxos críticos sem backend; testes de integração Go dependem de Postgres acessível (`INTEGRATION_DATABASE_URL`). Perfil de aplicação em BD (`PUT /profile`); compose sem `PROFILE_DATA_ROOT`. |

## Contexto de sessão (referência rápida)

- **TDD:** `docs/TDD.md`
- **Stack alvo:** Go/Echo (`apps/api/`) + React/Vite (`apps/web/`) + PostgreSQL + S3 + **Python (LangGraph, FastAPI, Playwright, boto3)** em `apps/worker/`
- **Contrato:** ver `design.md` — seção **Contrato Go ↔ Python**
