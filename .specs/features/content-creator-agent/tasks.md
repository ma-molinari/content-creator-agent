# Content Creator Agent — Tasks

**Design**: `.specs/features/content-creator-agent/design.md`
**Status**: Aprovado | Em execução — **Fase 1 (T1–T8) concluída**; Fase 2+ pendente

---

## Execution Plan

### Fase 1: Base — Backend Foundation (Sequencial)

```
T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8
```

### Fase 2: Core API (Paralelo após T3)

```
         ┌→ T9  [P] (GET /chats)
         ├→ T10 [P] (POST /chats)
T3 ──────┼→ T11 [P] (GET /chats/:id)
         ├→ T12 [P] (DELETE /chats/:id)
         └→ T13 [P] (S3 Service)
```
```
T9+T10+T11+T12+T13 ──→ T14 (limite 5 posts) ──→ T15 [P] (GET files)
                                               ──→ T16 [P] (GET files/download)
                                               ──→ T17 [P] (GET files/:fileId)
```

### Fase 3: Agent + Export (Sequencial após Fase 2)

```
T14 → T18 → T19 → T20 → T21 → T22 → T23
```

### Fase 4: Frontend (Paralelo com Fase 3, após T3)

```
T3 → T24 → T25 → T26 [P] ──┐
                  T27 [P] ──┤──→ T28 → T29 → T30 → T31 → T32 → T33
```

### Fase 5: Cron Job (Paralelo com Fase 4, após Fase 2)

```
T14 → T34 → T35
```

### Fase 6: QA & Deploy (Após todas as fases)

```
T36 [P] ──┐
T37 [P] ──┼──→ T38 → T39 → T40 → T41
T35 ──────┘
```

---

## Parallel Execution Map

```
FASE 1 (Sequencial — ~4d):
  T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8

FASE 2 (Paralelo após T3 — ~3.5d):
  Após T3:
    ├── T9  [P]
    ├── T10 [P]  ← podem rodar simultaneamente
    ├── T11 [P]
    ├── T12 [P]
    └── T13 [P]
  Após T9+T10+T11+T12+T13:
    T14
  Após T14:
    ├── T15 [P]
    ├── T16 [P]
    └── T17 [P]

FASE 3 (Sequencial após T14 — ~5d):
  T18 → T19 → T20 → T21 → T22 → T23

FASE 4 (Paralelo com Fase 3, após T3 — ~8d):
  T24 → T25
  Após T25:
    ├── T26 [P]
    └── T27 [P]
  Após T26+T27:
    T28 → T29 → T30 → T31 → T32 → T33

FASE 5 (Paralelo com Fase 4, após T14 — ~1.5d):
  T34 → T35

FASE 6 (Após todas — ~5d):
  ├── T36 [P]
  ├── T37 [P]  ← após T35
  └── (aguardar Fase 3 completa)
  Após T36+T37:
    T38 → T39 → T40 → T41

Caminho Crítico: T1→T2→T3→T4→T5→T6→T7→T8→T13→T14→T18→T19→T20→T21→T22→T23→T37→T38→T39→T40→T41
Total de tasks: 41 | Paralelizáveis: 15 | Fases: 6
Estimativa Total: ~27 dias
```

---

## Task Breakdown

---

### FASE 1 — BASE

---

### T1: Setup do projeto Golang

**What**: Inicializar o projeto Golang com Echo, estrutura de pacotes, Dockerfile e go.mod
**Where**: `backend/cmd/server/main.go`, `backend/go.mod`, `backend/Dockerfile`
**Depends on**: None
**Reuses**: Estrutura definida em `design.md` — seção API Layer; alinhar pastas e separação de camadas à rule [`engineering-backend-architect.md`](../../../.cursor/rules/engineering/engineering-backend-architect.md)
**Requirement**: AUTH-01 (fundação para todos os auth requirements)

**Done when**:
- [x] `go mod init` com módulo nomeado
- [x] Echo configurado com rota de health check `GET /health`
- [x] Dockerfile com `npx playwright install chromium` incluído
- [x] `docker build` executa sem erros
- [x] Estrutura de pacotes (`cmd` / `internal`) e decisões de camada coerentes com [`engineering-backend-architect.md`](../../../.cursor/rules/engineering/engineering-backend-architect.md)

**Verify**:
```bash
cd backend && go build ./...
docker build -t content-creator-agent-backend .
curl http://localhost:8080/health
```

**Commit**: `chore(backend): initialize Go project with Echo and Dockerfile`

---

### T2: Schema e migrations PostgreSQL

**What**: Criar arquivos de migration SQL com todas as tabelas, enums e índices do modelo de dados
**Where**: `backend/internal/db/migrations/`
**Depends on**: T1
**Reuses**: Modelo de dados em `design.md` — seção Data Models
**Requirement**: AUTH-01, POST-03, HIST-01

**Done when**:
- [x] Migration `001_create_enums.sql` cria `post_type_enum` e `role_enum`
- [x] Migration `002_create_users.sql` com todos os campos + índices
- [x] Migration `003_create_chats.sql` com FK para users + índices
- [x] Migration `004_create_chat_content.sql` com FK para chats + índices
- [x] Migration `005_create_chat_content_image.sql` com FK para chat_content + índices
- [x] Migration `006_create_chat_content_resume.sql` com FK única para chats + índices
- [x] Down migrations criadas para cada arquivo

**Verify**:
```bash
psql $DATABASE_URL -f backend/internal/db/migrations/001_create_enums.sql
# ... aplicar todas as migrations
psql $DATABASE_URL -c "\dt" # verificar todas as tabelas criadas
```

**Commit**: `feat(db): add PostgreSQL schema migrations with all tables and indexes`

---

### T3: Conexão GORM + configuração de ambiente

**What**: Configurar conexão GORM com PostgreSQL, rodar migrations e centralizar variáveis de ambiente
**Where**: `backend/internal/db/db.go`, `backend/.env.example`
**Depends on**: T2
**Reuses**: Modelos definidos em `design.md` — Data Models
**Requirement**: AUTH-01

**Done when**:
- [x] GORM conecta ao PostgreSQL via `DATABASE_URL`
- [x] Models Go mapeados (`User`, `Chat`, `ChatContent`, `ChatContentImage`, `ChatContentResume`)
- [x] `.env.example` documenta todas as variáveis obrigatórias (`DATABASE_URL`, `JWT_SECRET`, `AWS_*`, `OPENAI_API_KEY`)
- [x] Conexão falha com log claro se `DATABASE_URL` não estiver definida

**Verify**:
```bash
cd backend && go test ./internal/db/... -v
```

**Commit**: `feat(db): configure GORM connection and environment setup`

---

### T4: Endpoint POST /auth/register

**What**: Implementar handler, service e repository de registro com geração de securityKey
**Where**: `backend/internal/auth/handler.go`, `backend/internal/auth/service.go`, `backend/internal/auth/repository.go`
**Depends on**: T3
**Reuses**: Modelo `User` de `backend/internal/db/`
**Requirement**: AUTH-01, AUTH-02, AUTH-03

**Done when**:
- [x] `POST /auth/register` com body `{ email, password }` cria usuário
- [x] `securityKey` gerada com UUID v4 de alta entropia, exibida uma vez na resposta, armazenada como hash bcrypt (custo ≥ 12)
- [x] Email duplicado retorna `409 Conflict`
- [x] Senha com menos de 8 caracteres retorna `400 Bad Request`
- [x] Password armazenado como hash bcrypt (custo ≥ 12)

**Verify**:
```bash
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"senha123"}'
# Verificar resposta contém securityKey
# Verificar 409 ao repetir com mesmo email
```

**Commit**: `feat(auth): implement user registration with security key generation`

---

### T5: Endpoint POST /auth/login com JWT

**What**: Implementar handler de login retornando accessToken e configurando cookie httpOnly com refreshToken
**Where**: `backend/internal/auth/handler.go`, `backend/internal/auth/service.go`
**Depends on**: T4
**Reuses**: Service de auth de T4
**Requirement**: AUTH-04, AUTH-05

**Done when**:
- [x] `POST /auth/login` valida credenciais e retorna `{ accessToken }` (JWT 15 min)
- [x] Cookie `refresh_token` configurado: `httpOnly`, `Secure`, `SameSite=Strict`, validade 7 dias
- [x] Credenciais inválidas retornam `401 Unauthorized`
- [x] Access token contém `user_id` como claim

**Verify**:
```bash
curl -c cookies.txt -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"senha123"}'
# Verificar accessToken no body + cookie refresh_token nos headers
```

**Commit**: `feat(auth): implement login with JWT access token and httpOnly refresh cookie`

---

### T6: Middleware JWT + rota de renovação

**What**: Implementar middleware de validação JWT para rotas protegidas e endpoint `POST /auth/refresh`
**Where**: `backend/internal/middleware/jwt.go`, `backend/internal/auth/handler.go`
**Depends on**: T5
**Reuses**: Claims JWT de T5
**Requirement**: AUTH-06, AUTH-07

**Done when**:
- [x] Middleware extrai e valida JWT do header `Authorization: Bearer <token>`; injeta `user_id` no contexto
- [x] Rotas sem token retornam `401 Unauthorized`
- [x] `POST /auth/refresh` lê o cookie `refresh_token`, valida, retorna novo `accessToken`
- [x] Refresh token inválido/expirado retorna `401`

**Verify**:
```bash
# Sem token
curl http://localhost:8080/chats  # deve retornar 401
# Com token
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/chats  # deve retornar 200/[]
```

**Commit**: `feat(auth): add JWT middleware and token refresh endpoint`

---

### T7: Endpoint POST /auth/recover-password

**What**: Implementar recuperação de senha via securityKey
**Where**: `backend/internal/auth/handler.go`, `backend/internal/auth/service.go`
**Depends on**: T6
**Reuses**: Repository de auth de T4
**Requirement**: AUTH-08, AUTH-09

**Done when**:
- [x] `POST /auth/recover-password` com `{ email, securityKey, newPassword }` redefine a senha
- [x] securityKey incorreta retorna `403 Forbidden`
- [x] Email não encontrado retorna `404 Not Found`
- [x] Nova senha armazenada como hash bcrypt (custo ≥ 12)

**Verify**:
```bash
curl -X POST http://localhost:8080/auth/recover-password \
  -d '{"email":"test@test.com","securityKey":"<key>","newPassword":"novasenha123"}'
# Verificar login com nova senha funciona
```

**Commit**: `feat(auth): implement password recovery with security key validation`

---

### T8: Rate limiting + headers de segurança HTTP

**What**: Adicionar middleware de rate limiting in-memory e headers de segurança HTTP globais
**Where**: `backend/internal/middleware/rate_limit.go`, `backend/cmd/server/main.go`
**Depends on**: T6
**Reuses**: Middleware pattern de T6; headers, CORS e rate limiting conforme [`engineering-security-engineer.md`](../../../.cursor/rules/engineering/engineering-security-engineer.md) (defense in depth, falha segura)
**Requirement**: POST-09, SEC geral

**Done when**:
- [x] Rate limit por IP para `/auth/*`: máximo 20 requisições por 5 minutos
- [x] Rate limit por `user_id` para endpoints de LLM (mais restritivo que `/auth`)
- [x] Headers configurados: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, CORS restritivo
- [x] `429 Too Many Requests` retornado ao exceder limite

**Verify**:
```bash
# Enviar 25 requisições para /auth/login em sequência
# Verificar 429 após o limite
```

**Commit**: `feat(middleware): add in-memory rate limiting and HTTP security headers`

---

### FASE 2 — CORE API

---

### T9: Endpoint GET /chats [P]

**What**: Listar os últimos 5 chats do usuário autenticado
**Where**: `backend/internal/chat/handler.go`, `backend/internal/chat/repository.go`
**Depends on**: T3
**Reuses**: Middleware JWT de T6, modelo `Chat`
**Requirement**: HIST-01

**Done when**:
- [x] `GET /chats` retorna array de no máximo 5 chats do usuário, ordenados por `created_at DESC`
- [x] Chats de outros usuários nunca aparecem na listagem (filtro por `user_id` do JWT)
- [x] Retorna `[]` (array vazio) quando não há chats

**Verify**:
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/chats
# Verificar apenas chats do usuário autenticado
```

**Commit**: `feat(chat): add GET /chats endpoint returning last 5 chats`

---

### T10: Endpoint POST /chats [P]

**What**: Criar novo chat com tipo de post (single ou carousel)
**Where**: `backend/internal/chat/handler.go`, `backend/internal/chat/service.go`
**Depends on**: T3
**Reuses**: Repository de chat de T9
**Requirement**: POST-01

**Done when**:
- [x] `POST /chats` com `{ postType: "single" | "carousel" }` cria e retorna o chat criado
- [x] `postType` inválido retorna `400 Bad Request`
- [x] Chat criado com `user_id` do token JWT (nunca do body)

**Verify**:
```bash
curl -X POST http://localhost:8080/chats \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"postType":"carousel"}'
# Verificar retorno com ID do novo chat
```

**Commit**: `feat(chat): add POST /chats endpoint for chat creation`

---

### T11: Endpoint GET /chats/:id [P]

**What**: Retornar chat com suas mensagens pelo ID
**Where**: `backend/internal/chat/handler.go`
**Depends on**: T3
**Reuses**: Repository de chat de T9
**Requirement**: HIST-02, HIST-03

**Done when**:
- [x] `GET /chats/:id` retorna chat com todos os `ChatContent` e `ChatContentImage` associados
- [x] Chat de outro usuário retorna `403 Forbidden`
- [x] Chat não encontrado retorna `404 Not Found`

**Verify**:
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/chats/$CHAT_ID
# Testar com chat de outro usuário → deve retornar 403
```

**Commit**: `feat(chat): add GET /chats/:id endpoint with messages and isolation`

---

### T12: Endpoint DELETE /chats/:id [P]

**What**: Deletar chat, mensagens e arquivos S3 associados
**Where**: `backend/internal/chat/handler.go`, `backend/internal/chat/service.go`
**Depends on**: T3
**Reuses**: Repository de chat, Storage Service de T13
**Requirement**: HIST-04

**Done when**:
- [x] `DELETE /chats/:id` remove o chat, todos os `ChatContent`, `ChatContentImage` e chama `storage.DeleteMany` para os S3 keys
- [x] Chat de outro usuário retorna `403 Forbidden`
- [x] Chat não encontrado retorna `404 Not Found`
- [x] Retorna `204 No Content` em caso de sucesso

**Verify**:
```bash
curl -X DELETE -H "Authorization: Bearer $TOKEN" http://localhost:8080/chats/$CHAT_ID
# Verificar 204 + registros removidos do banco + arquivos removidos do S3
```

**Commit**: `feat(chat): add DELETE /chats/:id with cascading S3 file deletion`

---

### T13: S3 Storage Service [P]

**What**: Implementar cliente S3 com upload, geração de Signed URLs, delete e delete em lote
**Where**: `backend/internal/storage/s3.go`
**Depends on**: T3
**Reuses**: AWS SDK Go v2
**Requirement**: POST-03, POST-07, FILE-01, FILE-02, HIST-04

**Done when**:
- [x] `Upload(ctx, key, data)` faz upload com retry (backoff exponencial, 3 tentativas)
- [x] `GetSignedURL(ctx, key, expiry)` retorna URL assinada válida pelo tempo especificado
- [x] `Delete(ctx, key)` remove arquivo do S3
- [x] `DeleteMany(ctx, keys)` remove múltiplos arquivos em batch
- [x] Erros do S3 são logados e propagados com contexto claro

**Verify**:
```bash
cd backend && go test ./internal/storage/... -v
# Usar LocalStack ou S3 de teste para verificar upload/download/delete
```

**Commit**: `feat(storage): implement S3 service with retry and batch operations`

---

### T14: Lógica de limite de 5 chats por usuário

**What**: Implementar remoção automática do chat mais antigo ao criar o 6º chat
**Where**: `backend/internal/chat/service.go`
**Depends on**: T9, T10, T12, T13
**Reuses**: Service de chat, Storage Service
**Requirement**: POST-04

**Done when**:
- [x] Antes de criar novo chat, contar chats ativos do usuário
- [x] Se count ≥ 5: deletar o chat com `created_at` mais antigo (cascade: mensagens + S3)
- [x] Novo chat é criado após a remoção, sem erro para o usuário
- [x] Lógica testada com unitários cobrindo: 4 chats (sem remoção), 5 chats (remove 1), 1 chat (sem remoção)

**Verify**:
```bash
cd backend && go test ./internal/chat/... -run TestChatLimit -v
# Criar 6 chats via API e verificar que apenas 5 existem
```

**Commit**: `feat(chat): enforce 5-chat limit with automatic oldest chat removal`

---

### T15: Endpoint GET /chats/:id/files [P]

**What**: Listar arquivos gerados em um chat
**Where**: `backend/internal/chat/handler.go`
**Depends on**: T14
**Reuses**: Repository de chat, Storage Service
**Requirement**: FILE-01, FILE-03

**Done when**:
- [x] `GET /chats/:id/files` retorna array de `ChatContentImage` com `id`, `fileName`, `mimeType`, `downloadUrl` (Signed URL)
- [x] Chat de outro usuário retorna `403 Forbidden`
- [x] Chat sem arquivos retorna `[]`

**Verify**:
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/chats/$CHAT_ID/files
```

**Commit**: `feat(files): add GET /chats/:id/files endpoint with signed URLs`

---

### T16: Endpoint GET /chats/:id/files/download (zip) [P]

**What**: Gerar e retornar arquivo `.zip` com todos os JPEGs do chat
**Where**: `backend/internal/chat/handler.go`
**Depends on**: T14
**Reuses**: Storage Service, `archive/zip` da stdlib Go
**Requirement**: FILE-02, FILE-03

**Done when**:
- [x] `GET /chats/:id/files/download` baixa todos os JPEGs do S3 e os compacta em `.zip` em memória
- [x] Response com `Content-Type: application/zip` e `Content-Disposition: attachment; filename="slides-{chatId}.zip"`
- [x] Chat sem arquivos retorna `404 Not Found`
- [x] Chat de outro usuário retorna `403 Forbidden`

**Verify**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/chats/$CHAT_ID/files/download -o slides.zip
unzip -l slides.zip  # verificar conteúdo
```

**Commit**: `feat(files): add GET /chats/:id/files/download returning zip of all slides`

---

### T17: Endpoint GET /chats/:id/files/:fileId [P]

**What**: Download de arquivo JPEG individual pelo ID
**Where**: `backend/internal/chat/handler.go`
**Depends on**: T14
**Reuses**: Storage Service
**Requirement**: FILE-01, FILE-03

**Done when**:
- [x] `GET /chats/:id/files/:fileId` retorna o JPEG com `Content-Type: image/jpeg`
- [x] Arquivo de outro usuário retorna `403 Forbidden`
- [x] Arquivo não encontrado retorna `404 Not Found`

**Verify**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/chats/$CHAT_ID/files/$FILE_ID -o slide.jpg
file slide.jpg  # deve ser JPEG
```

**Commit**: `feat(files): add GET /chats/:id/files/:fileId for single slide download`

---

### FASE 3 — AGENT

---

### T18: Setup Langchain + cliente OpenAI

**What**: Configurar `tmc/langchaingo` com OpenAI GPT-5.4 Mini, limite de 4.000 tokens de saída
**Where**: `backend/internal/agent/llm.go`
**Depends on**: T14
**Reuses**: Variáveis de ambiente de T3 (`OPENAI_API_KEY`)
**Requirement**: POST-01

**Done when**:
- [ ] Cliente LLM configurado com `model: gpt-5.4-mini`, `max_tokens: 4000`
- [ ] Circuit breaker implementado: 3 tentativas com backoff exponencial
- [ ] Erro de API OpenAI logado e propagado com mensagem amigável
- [ ] Timeout configurado por requisição (ex.: 60s)

**Verify**:
```bash
cd backend && go test ./internal/agent/... -run TestLLMClient -v
# Mock da API OpenAI; testar resposta e comportamento de falha
```

**Commit**: `feat(agent): configure Langchain client with OpenAI GPT-5.4 Mini and circuit breaker`

---

### T19: Agent Service — Prompt Engineering Meta

**What**: Implementar pipeline de otimização de prompts do usuário antes de enviar ao LLM
**Where**: `backend/internal/agent/prompt_optimizer.go`
**Depends on**: T18
**Reuses**: Lógica da regra `.cursor/rules/prompt-engineering-meta.mdc` como instrução de sistema
**Requirement**: POST-01, POST-08

**Done when**:
- [ ] Prompt do usuário é enriquecido com a estrutura Persona/Contexto/Tarefa/Restrições/Formato
- [ ] Instrução de sistema inclui regras anti-prompt-injection (proibição de execução de comandos, escape de instruções do usuário)
- [ ] Input sanitizado antes de ser incluído no prompt (strip de tags HTML, caracteres de controle)
- [ ] Função exportada: `OptimizePrompt(ctx, userPrompt, userProfile) → (optimizedPrompt string, error)`

**Verify**:
```bash
cd backend && go test ./internal/agent/... -run TestPromptOptimizer -v
```

**Commit**: `feat(agent): implement prompt optimization pipeline with injection prevention`

---

### T20: Agent Service — Skill create-social-post

**What**: Integrar a skill `create-social-post` como instrução de sistema, gerando slides em HTML/CSS
**Where**: `backend/internal/agent/slide_generator.go`
**Depends on**: T19
**Reuses**: Workflow da skill `.cursor/skills/create-social-posts/SKILL.md`; perfil do usuário de `map-instagram-profile`
**Requirement**: POST-01, POST-02, SETUP-01, SETUP-02

**Done when**:
- [ ] Agent lê os arquivos de auditoria do usuário (`BRAND.md`, `AUDIT.md`) para construir o contexto de identidade visual
- [ ] Se arquivos ausentes: retorna erro com código `SETUP_REQUIRED` antes de chamar o LLM
- [ ] Resposta do LLM contém arquivos `slide-NN.html` separados por delimitador
- [ ] Função exportada: `GenerateSlides(ctx, userID, optimizedPrompt) → ([]SlideHTML, error)`

**Verify**:
```bash
cd backend && go test ./internal/agent/... -run TestSlideGenerator -v
# Mock da resposta LLM com HTML de slide válido
```

**Commit**: `feat(agent): integrate create-social-post skill for HTML/CSS slide generation`

---

### T21: Export Service — Playwright runner

**What**: Implementar serviço que executa `export-slides.js` para converter HTML em JPEG
**Where**: `backend/internal/export/playwright_runner.go`
**Depends on**: T20
**Reuses**: `scripts/export-slides.js` (existente)
**Requirement**: POST-02, POST-06

**Done when**:
- [ ] `ExportSlides(ctx, htmlPaths) → ([]string jpegPaths, error)` executa `node scripts/export-slides.js --export --confirm` via `os/exec`
- [ ] Stderr do processo filho capturado e logado
- [ ] Em caso de falha: HTML preservado em diretório temporário para re-tentativa; retorna erro descritivo
- [ ] Output: JPEGs com 768×1376px, qualidade 92
- [ ] Timeout por exportação configurável (padrão: 120s)

**Verify**:
```bash
cd backend && go test ./internal/export/... -v
# Testar com arquivo HTML de slide real
```

**Commit**: `feat(export): implement Playwright runner service for HTML-to-JPEG conversion`

---

### T22: Endpoint POST /chats/:id/messages

**What**: Implementar endpoint que orquestra Agent Service + Export Service + S3 e retorna a resposta ao usuário
**Where**: `backend/internal/chat/handler.go`, `backend/internal/chat/service.go`
**Depends on**: T21
**Reuses**: Agent Service (T20), Export Service (T21), Storage Service (T13), Chat Repository (T9)
**Requirement**: POST-01, POST-02, POST-03, POST-05, POST-06, POST-07, POST-08, POST-09, REPROMPT-01, REPROMPT-02

**Done when**:
- [ ] `POST /chats/:id/messages` com `{ content, attachments? }` processa o prompt e retorna `Message` com `files[]`
- [ ] Setup ausente retorna `400` com `code: "SETUP_REQUIRED"`
- [ ] Falha no LLM retorna `503` com mensagem amigável
- [ ] Falha no Playwright retorna `500` com mensagem amigável
- [ ] Falha no S3 (após retries) retorna `500`
- [ ] Para re-prompt: usa `chat_content_resume.summary` quando disponível; histórico completo quando ausente
- [ ] Rate limiting por `user_id` aplicado (middleware de T8)
- [ ] Mensagem do usuário e resposta do assistant salvas no banco (`ChatContent` + `ChatContentImage`)

**Verify**:
```bash
curl -X POST http://localhost:8080/chats/$CHAT_ID/messages \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"content":"Crie um post sobre produtividade"}'
# Verificar JPEGs no S3 + resposta com downloadUrls
```

**Commit**: `feat(chat): implement POST /chats/:id/messages orchestrating agent, export, and S3`

---

### T23: Verificação de setup map-instagram-profile

**What**: Implementar verificação se os arquivos de perfil do usuário estão configurados antes de processar mensagens
**Where**: `backend/internal/agent/profile_checker.go`
**Depends on**: T22
**Reuses**: Lógica de `setup.md` do `map-instagram-profile` skill
**Requirement**: SETUP-01, SETUP-02

**Done when**:
- [ ] `CheckProfileSetup(ctx, userID) → (bool, error)` verifica existência dos arquivos `BRAND.md` e `AUDIT.md` do usuário
- [ ] Endpoint `GET /setup/status` retorna `{ configured: bool }` para o frontend exibir bloqueio ou acesso
- [ ] T22 chama esta verificação antes de processar qualquer prompt

**Verify**:
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/setup/status
# { "configured": false } sem setup
# { "configured": true } com setup
```

**Commit**: `feat(agent): add profile setup verification for map-instagram-profile`

---

### FASE 4 — FRONTEND

Implementação da interface SHALL seguir [`engineering-frontend-developer.md`](../../../.cursor/rules/engineering/engineering-frontend-developer.md) em conjunto com `design.md`, `docs/layout.md` e `docs/brand.md`.

---

### T24: Setup React + estrutura base

**What**: Inicializar projeto React com Vite, Zustand, React Query, TailwindCSS e estrutura de diretórios
**Where**: `frontend/`
**Depends on**: T3
**Reuses**: Estrutura em `design.md` — seções **Frontend (React)** e **Documentação de UI e marca**; `docs/layout.md` (shell e rotas); `docs/brand.md` (base de tokens para tema); [`engineering-frontend-developer.md`](../../../.cursor/rules/engineering/engineering-frontend-developer.md) (padrões de código front-end)
**Requirement**: AUTH-04 (fundação para frontend)

**Done when**:
- [ ] `npm create vite@latest` com TypeScript + React
- [ ] Zustand configurado para `authStore` (accessToken, user)
- [ ] React Query configurado com `QueryClient` global
- [ ] TailwindCSS configurado com caminho preparado para mapear tokens de `docs/brand.md` (ex.: `theme.extend` ou CSS variables no `index.css`)
- [ ] Axios com interceptor: injeta `Authorization: Bearer $token` e detecta 401 para renovação automática via `POST /auth/refresh`
- [ ] React Router configurado com rotas: `/login`, `/register`, `/`, `/history`
- [ ] Rota `/` e `/history` protegidas (redirect para `/login` se não autenticado)

**Verify**:
```bash
cd frontend && npm run dev
# Verificar que app inicia sem erros em http://localhost:5173
```

**Commit**: `chore(frontend): initialize React project with Vite, Zustand, React Query, and routing`

---

### T25: Componentes base de layout e tema

**What**: Criar componentes de layout compartilhados (Navbar, PageContainer, LoadingSpinner, ErrorMessage)
**Where**: `frontend/src/components/`
**Depends on**: T24
**Reuses**: TailwindCSS de T24; token set e semântica de `docs/brand.md`; hierarquia de shell e espaçamento de `docs/layout.md`; [`engineering-frontend-developer.md`](../../../.cursor/rules/engineering/engineering-frontend-developer.md) (padrões de código front-end)
**Requirement**: AUTH-04

**Done when**:
- [ ] `Navbar` com logo e link para histórico (visível apenas quando autenticado)
- [ ] `PageContainer` para padding/max-width consistente
- [ ] `LoadingSpinner` para estados de loading
- [ ] `ErrorMessage` para exibição de erros de API
- [ ] Tema em `tailwind.config.ts` (e/ou `:root`) alinhado ao bloco recomendado em `docs/brand.md` (cores, raios, sombras, tipografia)
- [ ] Shell e densidade revisados contra `docs/ui/version_1.png`–`version_3.png` para área logada e `docs/ui/auth_1.png` para fluxo de auth (sem exigir paridade com todos os produtos das artes)

**Verify**:
```bash
cd frontend && npm run build  # sem erros de TypeScript
```

**Commit**: `feat(frontend): add base layout components and theme configuration`

---

### T26: Tela de Login [P]

**What**: Implementar página de login com form de email/senha e integração com `POST /auth/login`
**Where**: `frontend/src/pages/Login.tsx`, `frontend/src/api/auth.ts`
**Depends on**: T25
**Reuses**: Componentes de T25, React Query mutation; `docs/layout.md` — seção "Auth e marketing split"; captura `docs/ui/auth_1.png`; [`engineering-frontend-developer.md`](../../../.cursor/rules/engineering/engineering-frontend-developer.md) (padrões de código front-end)
**Requirement**: AUTH-04, AUTH-05

**Done when**:
- [ ] Form com campos email e senha com validação (campos obrigatórios, formato email)
- [ ] Layout de auth em duas colunas (formulário + painel marketing escuro) quando em viewport larga, empilhável em mobile, conforme `docs/layout.md` e referência `docs/ui/auth_1.png`
- [ ] Submit chama `POST /auth/login`; em sucesso: salva `accessToken` no Zustand e redireciona para `/`
- [ ] Erro de credenciais exibe mensagem inline no form
- [ ] Link para `/register` visível
- [ ] Loading state no botão durante a requisição

**Verify**:
```bash
# Abrir http://localhost:5173/login
# Testar login válido → redirecionamento para /
# Testar login inválido → mensagem de erro
```

**Commit**: `feat(frontend): implement login page with JWT auth integration`

---

### T27: Tela de Cadastro + modal da Security Key [P]

**What**: Implementar página de cadastro e modal de exibição da security key com instrução de guardar
**Where**: `frontend/src/pages/Register.tsx`, `frontend/src/components/SecurityKeyModal/`
**Depends on**: T25
**Reuses**: Componentes de T25, React Query mutation; `docs/layout.md` — "Auth e marketing split"; `docs/ui/auth_1.png`; [`engineering-frontend-developer.md`](../../../.cursor/rules/engineering/engineering-frontend-developer.md) (padrões de código front-end)
**Requirement**: AUTH-01, AUTH-02, AUTH-03

**Done when**:
- [ ] Form com email, senha e confirmação de senha com validação
- [ ] Mesmo padrão de split auth da T26 (form + painel marketing), alinhado a `docs/layout.md` e `docs/ui/auth_1.png`
- [ ] Submit chama `POST /auth/register`; em sucesso: exibe `SecurityKeyModal` com a chave
- [ ] `SecurityKeyModal` exibe a chave em destaque com botão de copiar, aviso em vermelho para guardar em local seguro, e botão "Entendido" (fecha modal e redireciona para `/login`)
- [ ] Erros de validação (409, 400) exibidos inline

**Verify**:
```bash
# Registrar novo usuário → verificar modal com securityKey
# Clicar em "Entendido" → redirecionar para /login
```

**Commit**: `feat(frontend): implement registration page and security key modal`

---

### T28: Interceptor JWT + renovação automática de token

**What**: Implementar interceptor Axios que detecta 401 e renova automaticamente o access token
**Where**: `frontend/src/lib/axios.ts`
**Depends on**: T26, T27
**Reuses**: Zustand authStore de T24; [`engineering-frontend-developer.md`](../../../.cursor/rules/engineering/engineering-frontend-developer.md) (padrões de código front-end)
**Requirement**: AUTH-06

**Done when**:
- [ ] Interceptor de resposta detecta `401` e chama `POST /auth/refresh` automaticamente
- [ ] Após renovação bem-sucedida: repete a requisição original com novo token
- [ ] Após renovação falha: limpa o Zustand e redireciona para `/login`
- [ ] Requisições simultâneas que recebem 401 não disparam múltiplas chamadas de refresh (queue de refresh)

**Verify**:
```bash
# Usar token expirado → verificar renovação transparente
# Usar refresh token inválido → verificar redirecionamento para /login
```

**Commit**: `feat(frontend): add Axios interceptor for transparent JWT token refresh`

---

### T29: Tela Principal — input rich text e bloqueio de setup

**What**: Implementar tela principal com input de prompt e verificação de setup inicial
**Where**: `frontend/src/pages/Chat.tsx`, `frontend/src/components/RichTextInput/`
**Depends on**: T28
**Reuses**: Componentes de T25, React Query para `GET /setup/status`; `docs/layout.md` — shell, empty state, área de chat; referências `docs/ui/version_1.png`, `version_2.png`, `version_3.png` para hierarquia (rail, main, composer) sem exigir feature parity com cada produto da arte; [`engineering-frontend-developer.md`](../../../.cursor/rules/engineering/engineering-frontend-developer.md) (padrões de código front-end)
**Requirement**: SETUP-01, SETUP-02, POST-01

**Done when**:
- [ ] Ao entrar na `/`, chama `GET /setup/status`
- [ ] Se `configured: false`: exibe banner de bloqueio com passo a passo do `map-instagram-profile` (sem mostrar input de prompt)
- [ ] Se `configured: true`: exibe o `RichTextInput` com placeholder descritivo
- [ ] `RichTextInput` suporta texto multilinha com formatação básica
- [ ] Seletor de tipo de post: "Single" | "Carrossel"
- [ ] Layout da tela principal (sidebar ou rail + área principal + composer na base) consistente com `docs/layout.md` e revisado contra `version_1`–`version_3` para proporção e leitura

**Verify**:
```bash
# Usuário sem setup → verificar banner de bloqueio
# Usuário com setup → verificar input de prompt visível
```

**Commit**: `feat(frontend): implement main chat page with setup gate and rich text input`

---

### T30: Tela Principal — envio de prompt e loading state

**What**: Implementar envio do prompt via `POST /chats/:id/messages` com estado de loading
**Where**: `frontend/src/pages/Chat.tsx`
**Depends on**: T29
**Reuses**: React Query mutation, RichTextInput de T29; `docs/layout.md` — "Composer / barra de entrada" e estados de feedback; `docs/brand.md` para feedback visual consistente; [`engineering-frontend-developer.md`](../../../.cursor/rules/engineering/engineering-frontend-developer.md) (padrões de código front-end)
**Requirement**: POST-01, POST-05, POST-06

**Done when**:
- [ ] Submit do form: cria chat (`POST /chats`) se não há chat ativo, depois envia mensagem (`POST /chats/:id/messages`)
- [ ] Durante processamento: input desabilitado + spinner com mensagem "Gerando post..."
- [ ] Erro do servidor exibe `ErrorMessage` com texto amigável (sem stack trace)
- [ ] Timeout de 90s no frontend com mensagem específica de timeout
- [ ] Composer/área de envio segue padrões de `docs/layout.md` (container largo, cantos arredondados, ações alinhadas); referência visual `version_1`–`version_3` conforme aplicável

**Verify**:
```bash
# Enviar prompt → verificar loading state → verificar resposta ou erro amigável
```

**Commit**: `feat(frontend): implement prompt submission with loading state and error handling`

---

### T31: Tela Principal — visualização de slides gerados

**What**: Implementar componente de visualização dos slides retornados pelo agente
**Where**: `frontend/src/components/SlideViewer/`
**Depends on**: T30
**Reuses**: React Query, URLs de download do S3; `docs/layout.md` — mensagens e "conteúdo rico" na thread (`version_2.png` como inspiração para cards/preview na conversa); `docs/brand.md` — elevação e bordas em cards; [`engineering-frontend-developer.md`](../../../.cursor/rules/engineering/engineering-frontend-developer.md) (padrões de código front-end)
**Requirement**: POST-01, FILE-01, FILE-02

**Done when**:
- [ ] `SlideViewer` exibe miniaturas de todos os slides retornados
- [ ] Clique em miniatura abre o slide em tamanho completo (modal ou lightbox)
- [ ] Botão "Download todos (.zip)" chama `GET /chats/:id/files/download`
- [ ] Botão "Download slide" individual por slide
- [ ] Indicador de número do slide (ex.: "1 / 5")
- [ ] Apresentação dos JPEGs na thread distingue claramente **preview do post** (output) do **chrome** do app (`docs/layout.md` — nota shell vs. conteúdo); sombras/bordas coerentes com `docs/brand.md`

**Verify**:
```bash
# Gerar post → verificar slides exibidos → testar downloads
```

**Commit**: `feat(frontend): implement slide viewer with individual and bulk download`

---

### T32: Tela de Histórico — lista de chats

**What**: Implementar página de histórico listando os últimos 5 chats
**Where**: `frontend/src/pages/History.tsx`, `frontend/src/components/ChatList/`
**Depends on**: T28
**Reuses**: React Query para `GET /chats`, componentes de T25; [`engineering-frontend-developer.md`](../../../.cursor/rules/engineering/engineering-frontend-developer.md) (padrões de código front-end)
**Requirement**: HIST-01, HIST-02

**Done when**:
- [ ] `/history` exibe lista de até 5 chats com: título, tipo de post (single/carrossel), data de criação e miniatura do primeiro slide
- [ ] Clicar em um chat navega para o chat em `/chats/:id` exibindo as mensagens
- [ ] Estado vazio com mensagem "Nenhum post criado ainda. Comece agora!"
- [ ] Ordenados do mais recente ao mais antigo

**Verify**:
```bash
# Navegar para /history → verificar lista de chats
# Clicar em chat → verificar abertura com mensagens
```

**Commit**: `feat(frontend): implement history page with chat list`

---

### T33: Tela de Histórico — re-prompt, download e delete

**What**: Adicionar ações de re-prompt, download e deleção na tela de histórico
**Where**: `frontend/src/pages/History.tsx`
**Depends on**: T32
**Reuses**: React Query mutations, SlideViewer de T31; [`engineering-frontend-developer.md`](../../../.cursor/rules/engineering/engineering-frontend-developer.md) (padrões de código front-end)
**Requirement**: REPROMPT-01, REPROMPT-02, HIST-04, FILE-01, FILE-02

**Done when**:
- [ ] Botão "Refinar" no chat abre input de re-prompt (envia nova mensagem para `POST /chats/:id/messages`)
- [ ] Botão "Download" exibe opções: "Todos (.zip)" e cada slide individual
- [ ] Botão "Deletar" exibe confirmação e chama `DELETE /chats/:id`; após sucesso: remove da lista
- [ ] Todas as ações aplicam estado de loading com feedback visual

**Verify**:
```bash
# Re-prompt em chat existente → verificar novos slides gerados
# Delete chat → verificar remoção da lista e confirmação
```

**Commit**: `feat(frontend): add re-prompt, download, and delete actions to history page`

---

### FASE 5 — CRON JOB

---

### T34: Setup do scheduler do Cron Job

**What**: Configurar o scheduler para o job de sumarização (rodando diariamente às 02:00 UTC)
**Where**: `backend/internal/cron/scheduler.go`
**Depends on**: T14
**Reuses**: `robfig/cron` ou goroutine com `time.Ticker`
**Requirement**: CRON-01

**Done when**:
- [ ] Scheduler configurado para rodar `SummarizeChats` diariamente às 02:00 UTC
- [ ] Job pode ser disparado manualmente via variável de ambiente `FORCE_SUMMARIZE=true` para testes
- [ ] Duração do job logada; alerta emitido se exceder 5 minutos

**Verify**:
```bash
FORCE_SUMMARIZE=true go run ./cmd/server/
# Verificar log de execução do job
```

**Commit**: `feat(cron): add daily chat summarization scheduler`

---

### T35: Lógica de sumarização de chats

**What**: Implementar a lógica que identifica chats elegíveis e sumariza via GPT-5.4 Mini
**Where**: `backend/internal/cron/summarizer.go`
**Depends on**: T34
**Reuses**: LLM client de T18, Repository de chat de T9
**Requirement**: CRON-01, CRON-02

**Done when**:
- [ ] Busca chats onde `chat_content.created_at` > `chat_content_resume.summarized_at` (ou sem resume)
- [ ] Para cada chat elegível: envia histórico completo ao GPT-5.4 Mini com instrução de sumarização compacta
- [ ] Salva/atualiza registro em `chat_content_resume` com `summary` e `summarized_at`
- [ ] Chats sem conteúdo novo são ignorados
- [ ] Logs de resumo: quantos chats processados, quantos ignorados, duração total

**Verify**:
```bash
FORCE_SUMMARIZE=true go run ./cmd/server/
# Verificar registros em chat_content_resume no banco
cd backend && go test ./internal/cron/... -v
```

**Commit**: `feat(cron): implement chat summarization logic with GPT-5.4 Mini`

---

### FASE 6 — QA & DEPLOY

---

### T36: Testes unitários (backend) [P]

**What**: Escrever testes unitários para services, helpers e validações do backend
**Where**: `backend/internal/**/*_test.go`
**Depends on**: T23
**Reuses**: `testing` nativo Go + `testify`; categorias de teste de segurança aplicáveis à API conforme *Security Test Coverage Checklist* em [`engineering-security-engineer.md`](../../../.cursor/rules/engineering/engineering-security-engineer.md)
**Requirement**: Todos os requirements de Fase 1–3

**Done when**:
- [ ] Cobertura > 75% em `internal/auth/`, `internal/chat/`, `internal/agent/`, `internal/export/`
- [ ] Mocks para dependências externas (OpenAI, S3, Playwright)
- [ ] Cenários críticos cobertos: autenticação, limite de 5 chats, prompt injection, falha no LLM, falha no S3
- [ ] Onde couber em testes unitários, cobrir itens da checklist de segurança da rule (ex.: token inválido/expirado, IDOR em recursos de chat/arquivo, validação de input, respostas de erro sem vazamento de stack ou detalhes internos); detalhe completo na rule

**Verify**:
```bash
cd backend && go test ./... -cover
# Verificar cobertura > 75%
```

**Commit**: `test(backend): add unit tests achieving >75% coverage`

---

### T37: Testes de integração (backend) [P]

**What**: Escrever testes de integração para os endpoints críticos com banco de dados de teste
**Where**: `backend/internal/**/*_integration_test.go`
**Depends on**: T35
**Reuses**: `httptest` Go + banco PostgreSQL de teste (Docker); *Security Test Coverage Checklist* em [`engineering-security-engineer.md`](../../../.cursor/rules/engineering/engineering-security-engineer.md) para fluxos HTTP (auth, autorização, rate limit quando exercitável em integração)
**Requirement**: AUTH-04, POST-01, HIST-01, HIST-04, FILE-02

**Done when**:
- [ ] Fluxo completo de auth (register → login → refresh → recover) testado
- [ ] CRUD de chats com isolamento de usuários testado
- [ ] Limite de 5 chats testado end-to-end
- [ ] Download zip testado
- [ ] Todos os cenários de `403`/`404` testados
- [ ] Cenários de segurança da API validados em integração onde aplicável (acesso cruzado a chat/arquivo de outro usuário, requisições sem/fora de token, `429` em endpoints com rate limit); lista completa na rule

**Verify**:
```bash
cd backend && go test ./... -tags integration -v
```

**Commit**: `test(backend): add integration tests for critical API flows`

---

### T38: Testes E2E (Playwright)

**What**: Escrever testes E2E cobrindo os happy paths e cenários de erro críticos
**Where**: `e2e/`
**Depends on**: T36, T37
**Reuses**: Playwright (já presente para export-slides); ambiente completo Docker; [`engineering-frontend-developer.md`](../../../.cursor/rules/engineering/engineering-frontend-developer.md) (fluxos críticos e expectativas de UX/a11y verificáveis em E2E)
**Requirement**: AUTH-01, POST-01, HIST-04, FILE-02

**Done when**:
- [ ] Fluxo: cadastro → login → criar post → visualizar slides → download zip
- [ ] Fluxo: login → histórico → re-prompt → deletar chat
- [ ] Fluxo: login sem setup → verificar bloqueio
- [ ] Fluxo: tentativa de acesso a chat de outro usuário → 403

**Verify**:
```bash
cd e2e && npx playwright test
```

**Commit**: `test(e2e): add Playwright E2E tests for critical user flows`

---

### T39: Setup Docker completo (docker-compose)

**What**: Criar docker-compose com todos os serviços para desenvolvimento e staging
**Where**: `docker-compose.yml`, `docker-compose.staging.yml`
**Depends on**: T38
**Reuses**: `backend/Dockerfile` de T1; Vite build para frontend
**Requirement**: Deploy geral

**Done when**:
- [ ] `docker-compose up` sobe: backend, frontend, PostgreSQL (com migrations automáticas)
- [ ] Variáveis de ambiente via `.env` file
- [ ] Health checks configurados para backend e PostgreSQL
- [ ] `docker-compose.staging.yml` com configurações de produção (sem hot reload)

**Verify**:
```bash
docker-compose up --build
curl http://localhost:8080/health  # deve retornar 200
```

**Commit**: `chore(docker): add docker-compose for development and staging environments`

---

### T40: Deploy staging + smoke tests

**What**: Fazer deploy completo em ambiente de staging e executar smoke tests manuais
**Where**: Ambiente de staging (cloud)
**Depends on**: T39
**Reuses**: docker-compose.staging.yml de T39
**Requirement**: Métricas de Sucesso da spec

**Done when**:
- [ ] Deploy bem-sucedido em staging
- [ ] Smoke tests passando: cadastro, login, criar post, download, histórico
- [ ] Latência p95 < 500ms (excluindo LLM) verificada via logs
- [ ] Tempo de geração de post < 15s verificado manualmente
- [ ] Nenhum erro 5xx nos logs após smoke tests

**Verify**:
```bash
# Executar checklist de smoke tests manualmente no ambiente de staging
```

**Commit**: `chore(deploy): staging deployment with smoke test verification`

---

### T41: Deploy produção + monitoramento ativo

**What**: Fazer rollout para produção com monitoramento ativo nas primeiras horas
**Where**: Ambiente de produção
**Depends on**: T40
**Reuses**: Configuração de staging de T40; alertas da spec (seção Monitoramento)
**Requirement**: Métricas de Sucesso da spec

**Done when**:
- [ ] Deploy produção bem-sucedido sem downtime
- [ ] Alertas configurados: taxa de erro > 5%, latência p95 > 5s, OpenAI inacessível
- [ ] Logs estruturados fluindo corretamente
- [ ] Plano de rollback documentado e testado (trocar imagem Docker; down migration se necessário)
- [ ] Monitoramento ativo por 2h após deploy

**Verify**:
```bash
# Verificar logs estruturados + métricas nas primeiras horas
# Verificar alertas configurados e ativos
```

**Commit**: `chore(deploy): production rollout with monitoring and rollback plan`

---

## Granularity Check

| Task | Escopo | Status |
|------|--------|--------|
| T1: Setup projeto Golang | 3 arquivos (main, go.mod, Dockerfile) — tightly coupled | ✅ Granular |
| T2: Migrations PostgreSQL | Múltiplos arquivos SQL — um por tabela, todos de migração | ✅ Granular |
| T3: GORM + env config | 2 arquivos (db.go, .env.example) — tightly coupled | ✅ Granular |
| T4: POST /auth/register | handler + service + repository — vertical slice completo | ✅ Granular |
| T5: POST /auth/login | handler + service (auth existente) | ✅ Granular |
| T6: JWT middleware + refresh | middleware + handler de refresh | ✅ Granular |
| T7: POST /auth/recover-password | handler + service (auth existente) | ✅ Granular |
| T8: Rate limiting + headers | middleware.go + registro no main.go | ✅ Granular |
| T9–T12: Endpoints de chat | 1 endpoint por task | ✅ Granular |
| T13: S3 Service | 1 arquivo de serviço completo | ✅ Granular |
| T14: Limite 5 chats | 1 função no service existente | ✅ Granular |
| T15–T17: Endpoints de arquivo | 1 endpoint por task | ✅ Granular |
| T18–T21: Agent pipeline | 1 componente por task (LLM, optimizer, generator, exporter) | ✅ Granular |
| T22: POST /chats/:id/messages | Orquestrador — integra componentes prontos; justificadamente único | ✅ Granular |
| T23: Profile checker | 1 função + 1 endpoint | ✅ Granular |
| T24–T33: Frontend | 1 página ou 1 componente por task | ✅ Granular |
| T34–T35: Cron Job | scheduler + lógica (separados intencionalmente) | ✅ Granular |
| T36–T38: Testes | 1 camada por task | ✅ Granular |
| T39–T41: Deploy | 1 ambiente por task | ✅ Granular |
