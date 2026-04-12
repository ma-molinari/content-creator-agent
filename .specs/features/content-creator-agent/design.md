# Content Creator Agent — Design

**Spec**: `.specs/features/content-creator-agent/spec.md`
**TDD Completo**: `docs/TDD.md`
**Status**: Aprovado

---

## Architecture Overview

O sistema é uma SPA React conectada a uma API REST em Golang/Echo que orquestra um Agent Service (Langchain + OpenAI), um Export Service (Playwright/Chromium), Amazon S3 e PostgreSQL.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
│  Auth │ Tela Principal (Rich Text + Slides) │ Histórico         │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST + JWT
┌──────────────────────────▼──────────────────────────────────────┐
│                      API (Golang/Echo)                          │
│  Middleware: JWT │ Rate Limit │ CORS │ Sanitização              │
│  Rotas: /auth/* │ /chats/* │ /chats/:id/files/*                 │
└──────┬────────────────────┬───────────────────────┬─────────────┘
       │ GORM               │ goroutine/call         │ goroutine/call
┌──────▼──────┐   ┌─────────▼─────────┐   ┌────────▼─────────────┐
│  PostgreSQL │   │   Agent Service   │   │    Export Service    │
│  (dados)    │   │ Langchain+OpenAI  │   │  export-slides.js    │
└─────────────┘   │ GPT-5.4 Mini      │   │  Playwright/Chromium │
                  │ Skills + Rules    │   │  → JPEG 768×1376px   │
                  └─────────┬─────────┘   └────────┬─────────────┘
                            │ HTML/CSS slides        │ JPEGs
                  ┌─────────▼────────────────────────▼─────────────┐
                  │                  Amazon S3                      │
                  │  slide-NN.html │ slide-NN.jpg                  │
                  └────────────────────────────────────────────────┘
```

**Fluxo principal (criação de post):**
```
1. Usuário → prompt → Frontend
2. Frontend → POST /chats/:id/messages → API
3. API valida JWT + rate limit + sanitiza input
4. API → Agent Service (Langchain)
5. Agent: Prompt Engineering Meta → create-social-post skill → GPT-5.4 Mini
6. GPT-5.4 Mini → slide-NN.html (um por slide) → Agent Service → API
7. API → Export Service (executa export-slides.js --export --confirm)
8. Export Service → slide-NN.jpg (768×1376px, qualidade 92)
9. API → upload JPEGs ao S3 + salvar referências no banco
10. API → resposta com downloadUrls → Frontend → exibe slides
```

---

## Documentação de UI e marca (front-end)

Antes de implementar telas, ler **[`docs/layout.md`](../../../docs/layout.md)** (estrutura, hierarquia, componentes sugeridos, UX/a11y) e **[`docs/brand.md`](../../../docs/brand.md)** (tokens CSS, tipografia, sombras, resolução de conflitos entre referências).

| Screenshot | Caminho | O que extrair para este produto |
|------------|---------|----------------------------------|
| Talk Data to Me (empty + rail) | `docs/ui/version_1.png` | Rail estreita, estado ativo na nav, empty state centrado, chips de atalho, composer básico (anexo, contador, enviar) |
| Maskara.ai (thread) | `docs/ui/version_2.png` | Thread de mensagens, cards de arquivo, preview rico de conteúdo, composer com ações secundárias (ex.: voz) |
| Aplot AI (app denso) | `docs/ui/version_3.png` | Sidebar com busca/histórico, top bar com ações, feature cards, modos no composer, sombras suaves |
| CoLabs (auth) | `docs/ui/auth_1.png` | Auth em colunas: formulário claro + painel marketing escuro, inputs e CTA full-width |

**Governança:** papéis **UI Designer** e **UX Architect** → `docs/layout.md`; **Brand Guardian** → `docs/brand.md`. Complemento opcional: [`.cursor/rules/design/design-brand-guardian.md`](../../../.cursor/rules/design/design-brand-guardian.md).

**Implementação:** mapear cores, raios, sombras e tipografia ao bloco `:root` recomendado em `docs/brand.md` (Tailwind `theme.extend` ou variáveis CSS). Estrutura de shell (sidebar/main), thread, empty state e **ComposerBar** por slots seguem `docs/layout.md`. Estados de carregamento, erro e vazio alinham-se ao handoff em `docs/layout.md` (“Handoff para implementação”).

**Nota:** os **JPEGs dos slides** gerados pelo agente são o *output* editorial; a *casca* da aplicação (login, chat, histórico) segue as referências acima — não confundir preview de slide com o shell do app.

### Engenharia de implementação (React)

Todo código front-end deste produto SHALL seguir a rule **[`engineering-frontend-developer.md`](../../../.cursor/rules/engineering/engineering-frontend-developer.md)** além de `docs/layout.md` e `docs/brand.md`. Ela é o guia normativo de **padronização e construção de código** (não substitui decisões de UI/marca já documentadas).

- TypeScript e componentes com props tipadas; estrutura de pastas e nomes alinhados ao inventário de `docs/layout.md` quando aplicável.
- HTML semântico; ARIA e rótulos onde necessário; navegação por teclado e compatibilidade com leitores de tela (alvo WCAG 2.1 AA).
- Layout mobile-first; estados de carregamento, erro e vazio consistentes e acessíveis; feedback de erro sem expor detalhes técnicos.
- Performance: code splitting / lazy loading quando fizer sentido; atenção a bundle e assets; alinhamento às práticas da rule (Core Web Vitals quando mensurável).
- Testes: cobertura de componentes e fluxos críticos coerente com as entregas esperadas (unit/integration/E2E conforme fase do projeto).

### Engenharia de implementação (Golang / backend)

Todo código backend deste produto em `backend/` SHALL seguir a rule **[`engineering-backend-architect.md`](../../../.cursor/rules/engineering/engineering-backend-architect.md)** e a rule **[`engineering-security-engineer.md`](../../../.cursor/rules/engineering/engineering-security-engineer.md)** além deste design e de `docs/TDD.md`. São os guias normativos de **arquitetura, camadas e segurança** (não substituem endpoints e modelos já definidos na spec).

- **Backend Architect**: `cmd` / `internal`, contratos de handlers, services e repositories; GORM e migrations; integrações (S3, OpenAI, subprocesso do export); circuit breaker e retry já descritos aqui; métricas e latência alinhadas aos Success Criteria da spec.
- **Security Engineer**: validação nas fronteiras (JSON/body, IDs); autorização e prevenção de IDOR em `/chats/:id` e arquivos; JWT (claims, refresh, rejeição de algoritmos inseguros); segredos fora de código e logs; headers HTTP, CORS e rate limiting; dependências (pinning, SBOM onde aplicável); testes alinhados à *Security Test Coverage Checklist* da rule (autenticação, autorização, input, erros sem vazamento em produção, rate limit — ver a rule para a lista completa).

---

## Code Reuse Analysis

### Componentes Existentes a Aproveitar

| Componente | Localização | Como Usar |
|------------|-------------|-----------|
| `export-slides.js` | `scripts/export-slides.js` | Executor principal do Export Service — chamar via processo filho com flags `--export --confirm` |
| Skill `create-social-post` | `.cursor/skills/create-social-posts/SKILL.md` | Integrar como parte do pipeline do Agent Service via instrução de sistema |
| Skill `map-instagram-profile` | `.cursor/skills/map-instagram-profile/SKILL.md` | Estrutura de referência para perfil do usuário; Agent Service lê os arquivos de auditoria |
| Regra `prompt-engineering-meta` | `.cursor/rules/prompt-engineering-meta.mdc` | Template de otimização de prompts aplicado pelo Agent Service antes de chamar o LLM |

### Pontos de Integração

| Sistema | Método de Integração |
|---------|---------------------|
| OpenAI (GPT-5.4 Mini) | Langchain Go client — chamadas via Agent Service com limite de 4.000 tokens de saída |
| Amazon S3 | AWS SDK Go v2 — upload multipart, geração de Signed URLs para download, delete por key |
| PostgreSQL | GORM com migrations versionadas — modelos: `User`, `Chat`, `ChatContent`, `ChatContentImage`, `ChatContentResume` |
| Playwright/Chromium | Processo filho via `os/exec` — executa `node scripts/export-slides.js` com flags; Chromium instalado no Dockerfile |

---

## Components

### API Layer (Golang/Echo)

- **Propósito**: Roteamento, autenticação JWT, rate limiting, validação, orquestração entre Agent Service e Export Service
- **Normativo**: a implementação SHALL obedecer às rules [`engineering-backend-architect.md`](../../../.cursor/rules/engineering/engineering-backend-architect.md) e [`engineering-security-engineer.md`](../../../.cursor/rules/engineering/engineering-security-engineer.md) além da estrutura e middleware listados abaixo.
- **Localização**: `backend/`
- **Estrutura de pacotes**:
  ```
  backend/
  ├── cmd/server/          # entrypoint main.go
  ├── internal/
  │   ├── auth/            # handlers, service, middleware JWT
  │   ├── chat/            # handlers, service, repository
  │   ├── agent/           # agent service (Langchain integration)
  │   ├── export/          # export service (Playwright runner)
  │   ├── storage/         # S3 client
  │   ├── db/              # GORM setup, migrations
  │   └── middleware/      # rate limit, cors, sanitize
  ├── Dockerfile
  └── go.mod
  ```
- **Interfaces principais**:
  - `AuthHandler`: `Register`, `Login`, `Refresh`, `RecoverPassword`
  - `ChatHandler`: `List`, `Create`, `Get`, `Delete`, `SendMessage`
  - `FileHandler`: `ListFiles`, `DownloadSingle`, `DownloadAll`

### Agent Service

- **Propósito**: Recebe o prompt do usuário, aplica `Prompt Engineering Meta`, chama a skill `create-social-post` e retorna o HTML/CSS dos slides
- **Localização**: `backend/internal/agent/`
- **Interfaces**:
  - `ProcessMessage(ctx, userID, chatID, prompt, attachments) → ([]SlideHTML, error)`
- **Dependências**: Langchain Go, OpenAI API Key, perfil do usuário (arquivos `map-instagram-profile`)
- **Limite**: 4.000 tokens de saída por requisição

### Export Service

- **Propósito**: Renderiza arquivos `slide-NN.html` em JPEGs via Playwright/Chromium headless
- **Localização**: `backend/internal/export/`
- **Interfaces**:
  - `ExportSlides(ctx, htmlPaths []string) → ([]string jpegPaths, error)`
- **Dependências**: Node.js + `scripts/export-slides.js` + Chromium (instalado via `npx playwright install chromium` no Dockerfile)
- **Configuração de output**: 768×1376px, qualidade JPEG 92
- **Error handling**: Captura stderr do processo filho; preserva HTML em caso de falha para re-tentativa

### Storage Service (S3)

- **Propósito**: Upload, geração de Signed URLs, download e deleção de arquivos
- **Localização**: `backend/internal/storage/`
- **Interfaces**:
  - `Upload(ctx, key, data) → error`
  - `GetSignedURL(ctx, key, expiry) → (string, error)`
  - `Delete(ctx, key) → error`
  - `DeleteMany(ctx, keys []string) → error`
- **Retry**: Backoff exponencial com 3 tentativas no upload

### Auth Middleware

- **Propósito**: Validar JWT em todas as rotas exceto `/auth/*`; extrair `user_id` e injetar no contexto da requisição
- **Localização**: `backend/internal/middleware/`
- **Interfaces**:
  - `JWTMiddleware() echo.MiddlewareFunc`
  - `RateLimitMiddleware(config RateLimitConfig) echo.MiddlewareFunc`

### Frontend (React)

- **Propósito**: Interface do usuário — autenticação, criação de posts, histórico, download
- **Localização**: `frontend/`
- **Stack**: React + Vite + Zustand (auth state) + React Query (server state) + TailwindCSS
- **Padrões de implementação**: [`engineering-frontend-developer.md`](../../../.cursor/rules/engineering/engineering-frontend-developer.md) — referência única para qualidade de código front-end (acessibilidade, performance, testes, padrões de componente).
- **UI e tema**: `tailwind.config` / CSS global deve refletir o token set de [`docs/brand.md`](../../../docs/brand.md). Layout (AppShell, rail, área principal, composer) e nomes de componentes podem seguir o inventário sugerido em [`docs/layout.md`](../../../docs/layout.md) (ex.: `ComposerBar`, `EmptyChatState`); a árvore abaixo permanece a referência mínima de pastas — renomear ou decompor conforme esse inventário quando útil.
- **Estrutura**:
  ```
  frontend/
  ├── src/
  │   ├── pages/
  │   │   ├── Login.tsx
  │   │   ├── Register.tsx
  │   │   ├── Chat.tsx        # tela principal
  │   │   └── History.tsx     # histórico
  │   ├── components/
  │   │   ├── RichTextInput/
  │   │   ├── SlideViewer/
  │   │   ├── ChatList/
  │   │   └── SecurityKeyModal/
  │   ├── stores/             # Zustand
  │   ├── api/                # React Query hooks + axios
  │   └── lib/                # utils, interceptors JWT
  └── vite.config.ts
  ```
- **Auth token strategy**: `accessToken` em memória (variável Zustand); `refreshToken` em cookie httpOnly (gerenciado pelo browser); interceptor Axios detecta 401 e chama `POST /auth/refresh` automaticamente

### Cron Job

- **Propósito**: Sumarizar diariamente chats com conteúdo novo para reduzir custo de tokens
- **Localização**: `backend/internal/cron/`
- **Interfaces**:
  - `SummarizeChats(ctx) → error`
- **Scheduler**: `robfig/cron` ou goroutine com `time.Ticker` — roda em horário de baixo tráfego (ex.: 02:00 UTC)

---

## Data Models

### User
```go
type User struct {
    ID              uuid.UUID `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
    Email           string    `gorm:"uniqueIndex;not null"`
    PasswordHash    string    `gorm:"not null"`
    SecurityKeyHash string    `gorm:"not null"`
    CreatedAt       time.Time
    UpdatedAt       time.Time
}
```

### Chat
```go
type Chat struct {
    ID        uuid.UUID        `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
    UserID    uuid.UUID        `gorm:"type:uuid;index;not null"`
    Title     string           `gorm:"size:255"`
    PostType  string           `gorm:"type:post_type_enum"` // 'single' | 'carousel'
    CreatedAt time.Time        `gorm:"index"`
    UpdatedAt time.Time
    Contents  []ChatContent
    Resume    *ChatContentResume
}
```

### ChatContent
```go
type ChatContent struct {
    ID        uuid.UUID          `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
    ChatID    uuid.UUID          `gorm:"type:uuid;index;not null"`
    Role      string             `gorm:"type:role_enum"` // 'user' | 'assistant'
    Content   string             `gorm:"type:text"`
    CreatedAt time.Time          `gorm:"index"`
    Images    []ChatContentImage
}
```

### ChatContentImage
```go
type ChatContentImage struct {
    ID            uuid.UUID `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
    ChatContentID uuid.UUID `gorm:"type:uuid;index;not null"`
    S3Key         string    `gorm:"not null"`
    FileName      string    `gorm:"size:255"`
    MimeType      string    `gorm:"size:100"`
    CreatedAt     time.Time
}
```

### ChatContentResume
```go
type ChatContentResume struct {
    ID            uuid.UUID `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
    ChatID        uuid.UUID `gorm:"type:uuid;uniqueIndex;not null"`
    Summary       string    `gorm:"type:text"`
    LastContentAt time.Time
    SummarizedAt  time.Time
}
```

**Relacionamentos**:
- `User` 1:N `Chat` (isolamento total por `user_id`)
- `Chat` 1:N `ChatContent`
- `ChatContent` 1:N `ChatContentImage`
- `Chat` 1:0..1 `ChatContentResume`

---

## Error Handling Strategy

| Cenário de Erro | Tratamento | Impacto ao Usuário |
|-----------------|------------|--------------------|
| OpenAI API indisponível | Circuit breaker + retry com backoff (3x); retorna `503` após esgotar tentativas | "Serviço temporariamente indisponível. Tente novamente em instantes." |
| Playwright crash / timeout | Captura stderr; preserva HTML gerado; retorna `500` | "Ocorreu um erro ao gerar as imagens. Tente novamente." |
| Upload S3 falha | Retry com backoff (3x); transação não conclui sem S3 salvo com sucesso | "Erro ao salvar as imagens. Tente novamente." |
| Chromium não instalado | Log de erro crítico no startup; retorna `503` | "Serviço de exportação indisponível. Contate o suporte." |
| JWT expirado | Frontend intercepta 401 → renova via refresh token automaticamente | Transparente para o usuário |
| Refresh token inválido/expirado | Retorna `401`; frontend redireciona para `/login` | Usuário vê tela de login |
| Input com prompt injection | Sanitizado antes de enviar ao LLM; instrução de sistema bloqueia execução | Conteúdo sanitizado é processado normalmente |
| Rate limit excedido | Retorna `429 Too Many Requests` | "Muitas requisições. Aguarde alguns instantes." |
| Chat não encontrado | `404 Not Found` | Mensagem de erro descritiva |
| Acesso a recurso de outro usuário | `403 Forbidden` | Mensagem genérica de permissão negada |

---

## Technical Decisions

| Decisão | Escolha | Rationale |
|---------|---------|-----------|
| Geração de imagens | HTML/CSS via LLM → Playwright → JPEG | Reutiliza `export-slides.js` existente; sem custo adicional de modelo de imagem; slides consistentes com design code |
| Armazenamento de refresh token | Cookie httpOnly + Secure + SameSite=Strict | Proteção XSS (JS não acessa) + proteção CSRF (SameSite=Strict) |
| Access token location | Memória (Zustand) | Nunca em localStorage; perdido ao fechar a aba (intencionalmente) |
| Rate limiting V1 | In-memory (middleware Echo) | Zero dependência de Redis; Redis adotado no V2 para escala horizontal |
| Limite de chats | 5 chats por usuário (remoção automática do mais antigo) | Controle de storage S3 e custo; usuário pode deletar manualmente qualquer chat |
| Contexto para re-prompt | Resumo (`chat_content_resume`) quando disponível; histórico completo quando ausente | Reduz custo de tokens significativamente após cron job de sumarização |
| Migrations | GORM Auto-Migrate em desenvolvimento; arquivos SQL versionados em staging/produção | Down migrations obrigatórias para rollback seguro |

---

## Research Notes

| Tópico | Fonte | Finding |
|--------|-------|---------|
| Langchain Go | docs/TDD.md + pesquisa | Usar `tmc/langchaingo` — biblioteca Go com suporte a OpenAI, prompts e chains |
| Playwright no Docker | docs/TDD.md | `npx playwright install chromium` no Dockerfile; validar no CI |
| GORM enum fields | docs/TDD.md | Declarar como `type:post_type_enum` e criar ENUM no PostgreSQL via migration |
| bcrypt cost | docs/TDD.md | Custo ≥ 12 para senhas e security keys |
| RSA em trânsito | docs/TDD.md | Campos sensíveis (senha, security key) adicionalmente criptografados com RSA antes de sair do frontend; backend descriptografa antes de processar |
