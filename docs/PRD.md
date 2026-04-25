# Content Creator Agent

Um serviço web focado na criação de posts em redes sociais, seguindo boas práticas e a identidade visual do usuário.

## Sobre

O agente destina-se **apenas** à criação de posts no **Instagram**, usando regras e *skills* do repositório (p.ex. `create-social-post`, *Prompt Engineering Meta*). Os formatos suportados são **post single** (um arquivo) e **post carrossel** (N slides).

Os posts respeitam a identidade visual: melhorias são permitidas **dentro** da paleta e do tom já definidos.

## Perfil, auditoria e referências (V1)

No **V1** o usuário configura o perfil **na aplicação**: textos de **auditoria** e **marca** (e, opcionalmente, até 8 imagens de referência enviadas para o S3) via `GET`/`PUT /profile` e anexos de referência. O *gate* de criação exige `audit_text` e `brand_text` preenchidos (`GET /setup/status`); sem isso, `POST /chats/:id/messages` responde com erro de configuração (ver `docs/ARCHITECTURE.md`).

A skill **`map-instagram-profile`** e a pasta `instagram-audits/` descrevem a **estrutura de captura offline** (auditoria por screenshots e ficheiros `AUDIT.md` / `BRAND.md`) que pode alimentar o conteúdo do perfil; é documentação e fluxo de *intake*, não um substituto do armazenamento em base de dados.

**V2+ (direção):** experiência ainda mais guiada de *onboarding* a partir de capturas, ou automatismos adicionais — ver `docs/STRUCTURE.md`.

## Conta e acesso

- **Cadastro**, **recuperação de senha** e **login** na interface.
- No cadastro é mostrada **uma chave de segurança** (a guardar em local seguro); é necessária na recuperação de senha.
- Acesso **por usuário**: cada um só vê e altera os seus dados e conteúdos. Rotas de negócio exigem autenticação (JWT: *access* em memória no cliente, *refresh* em cookie HttpOnly — ver `docs/CONVENTIONS.md`).

## Experiência principal e histórico

- **Tela principal** com entrada de texto (e possibilidade de anexar imagens de referência, conforme a UI) e, quando aplicável, apoio a bons padrões de *prompt* (alinhado a *Prompt Engineering Meta* e `create-social-post`).

- A geração de slides é **assíncrona**: a API responde `202` com `jobId` e o cliente consulta o estado do trabalho até conclusão; depois há visualização e *download* de ficheiro único ou `.zip` (ver `docs/ARCHITECTURE.md`).

- **Histórico:** até **5** chats ativos por usuário; ao criar um 6.º, remove-se o mais antigo (e artefatos S3 associados) ou o usuário pode apagar manualmente. Download em `.jpg` (slides), novas mensagens no mesmo chat para iteração.

## Trabalho do agente e sumarização

- Interface de chat no estilo de produtos de mercado; *prompts* alinhados a *Prompt Engineering Meta* e contextualizados com a skill `create-social-post` (regras em `.cursor/`).

- **Cron diário** (API Go, `SUMMARIZE_CRON`, predefinido `0 2 * * *` UTC): condensa o histórico de chats com conteúdo novo para reduzir tokens em reutilizações; usa o cliente OpenAI na API (modelo configurado no código, p.ex. `GPT4oMini` no sumarizador). Só corre se `OPENAI_API_KEY` estiver definida.

## Segurança

- **Em trânsito:** TLS (HTTPS) em produção; refresh token em cookie com `COOKIE_SECURE` em HTTPS (`docs/RUNBOOK.md`).
- **No servidor:** palavras-passe e chave de segurança com *hash* (bcrypt); *rate limiting* na API, sanitização de entrada, boas práticas contra *prompt injection* e *SQL injection* (GORM parametrizado). CORS com origens explícitas.
- Criptografia **RSA** extra em cliente ↔ API está **prevista** como evolução (`apps/web/src/lib/crypto.ts`); o V1 transporta *password* em JSON sobre HTTPS com *hash* no servidor.

## Tecnologia (alinhada a `docs/STACK.md`)

### Front-end

- React (Vite), TypeScript, React Router, TanStack Query, Zustand, Zod, Tailwind, axios, *shadcn*-style UI onde aplicável.

### API (back-end)

- Go, Echo, GORM, PostgreSQL (migrações `golang-migrate` em `apps/api/internal/db/migrations/`), `httptest` e testes de integração com tag `integration`.
- Amazon S3 (SDK v2) para slides e referências; URLs presignadas (TTL documentado em `docs/INTEGRATIONS.md`).

### Worker (processamento)

- Python, **FastAPI** + Uvicorn, **LangGraph**, LangChain-OpenAI, **Playwright** (Chromium) para HTML → JPEG, boto3 para S3. *Dispatch* `POST {WORKER_URL}/jobs` e *callback* `POST /internal/jobs/:id/complete` com `X-Worker-API-Key`.

### LLM (geração e suporte)

- **Worker:** OpenAI — p.ex. `gpt-4o-mini` (geração de blocos HTML de slides), `gpt-4o` (visão / otimização de *brief*), conforme nós em `apps/worker/app/nodes/` e `docs/INTEGRATIONS.md`.
- **API (sumarização):** OpenAI via `sashabaranov/go-openai`, modelo alinhado ao código do sumarizador.

### Banco e rede

- **PostgreSQL** (16 no Compose).
- **Redis:** opcional; o *rate limit* V1 é em memória no processo (`docs/CONCERNS.md` — considerar Redis em escala horizontal).

### Tabelas (conceito)

- `users` (incl. `role`), `chats`, `chat_content`, `chat_content_image`, `chat_content_resume`, **`jobs`**, **`user_profiles`**, **`user_profile_references`**.

*Campos e enums:* ver `apps/api/internal/db/models.go` e migrações SQL.

## Documentação de apoio

- Arquitetura e fluxos: `docs/ARCHITECTURE.md`, `docs/INTEGRATIONS.md`, `docs/STRUCTURE.md`, `docs/RUNBOOK.md`, `docs/TESTING.md`, `docs/ui-guidelines.md`.
