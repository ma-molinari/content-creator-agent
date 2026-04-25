# Content Creator Agent — Especificação

**Referência TDD**: `docs/TDD.md`

**Arquitetura de processamento**: [`docs/ARCHITECTURE.md`](../../../docs/ARCHITECTURE.md) (API Go, worker Python LangGraph, jobs assíncronos; ver também [`docs/INTEGRATIONS.md`](../../../docs/INTEGRATIONS.md))

**Referências de front-end**: [`docs/ui-guidelines.md`](../../../docs/ui-guidelines.md) (estrutura, padrões de UI, tokens e marca). Capturas de referência em `docs/ui/`: `version_1.png`, `version_2.png`, `version_3.png`, `auth_1.png`. **Implementação de código** (padrões React/TypeScript, semântica e ARIA, performance, testes): seguir a rule [`engineering-frontend-developer.md`](../../../.cursor/rules/engineering/engineering-frontend-developer.md) — complementa layout e marca (o *o quê* e *como parece* permanecem em `docs/ui-guidelines.md`; o *como codificar* interfaces segue a rule).

**Implementação backend (Go)**: seguir [`engineering-backend-architect.md`](../../../.cursor/rules/engineering/engineering-backend-architect.md) (arquitetura de API, persistência, confiabilidade, performance e observabilidade alinhadas ao produto) e [`engineering-security-engineer.md`](../../../.cursor/rules/engineering/engineering-security-engineer.md) (limites de confiança, hardening, SDLC de segurança e práticas OWASP/API). O *o quê* (endpoints, modelos, fluxos) permanece nesta spec e em `docs/TDD.md`; o *como implementar* o servidor e integrações de forma consistente e segura segue essas rules (sem duplicar o conteúdo integral das rules aqui).

**Status**: Aprovado

---

## Problem Statement

Criadores de conteúdo, social media managers e empreendedores digitais precisam produzir posts para Instagram que respeitam identidade visual consolidada. Ferramentas genéricas de IA não conhecem a paleta, tipografia ou tom de voz da marca, e o processo manual é lento, inconsistente e sujeito a erros de identidade visual.

## Goals

- [ ] Permitir que qualquer usuário autenticado gere posts de Instagram (single e carrossel) via prompt em linguagem natural, respeitando automaticamente as diretrizes visuais e de comunicação da marca
- [ ] Oferecer histórico de posts criados com capacidade de refinamento (re-prompt), download e exclusão
- [ ] Garantir isolamento total de dados por usuário e proteção contra abusos (rate limiting, sanitização, prompt injection)

## Out of Scope

| Feature | Motivo |
|---------|--------|
| Tela de configuração de perfil / upload de arquivos de referência | V2 — estrutura `map-instagram-profile` é configurada manualmente no V1 |
| Publicação direta no Instagram via API | V2 |
| Suporte a outras redes sociais | V2 |
| Análise de performance dos posts | V2 |
| Plano de assinatura / cobrança | V2 |
| Multi-tenancy / workspaces compartilhados | V2 |
| Suporte a múltiplos idiomas na interface | Somente PT-BR no V1 |
| Redis como dependência obrigatória | Opcional no V1 |

---

## User Stories

### P1: Cadastro de Usuário — MVP

**User Story**: Como novo usuário, quero me cadastrar com email e senha e receber uma chave única de segurança para que eu possa recuperar minha conta se esquecer a senha.

**Por que P1**: Sem autenticação, nenhuma funcionalidade do sistema está acessível.

**Acceptance Criteria**:

1. WHEN o usuário envia `POST /auth/register` com email e senha válidos THEN o sistema SHALL criar a conta, gerar uma `securityKey` de alta entropia, exibi-la **uma única vez** na resposta e armazená-la como hash bcrypt no banco
2. WHEN o email já existe no banco THEN o sistema SHALL retornar `409 Conflict`
3. WHEN o usuário envia senha com menos de 8 caracteres THEN o sistema SHALL retornar `400 Bad Request` com mensagem descritiva
4. WHEN o cadastro é concluído THEN o frontend SHALL exibir a chave de segurança com instrução clara de guardar em local seguro

**Independent Test**: Chamar `POST /auth/register` com dados válidos, verificar que retorna `securityKey` e que novo registro existe no banco.

---

### P1: Autenticação e Renovação de Sessão — MVP

**User Story**: Como usuário cadastrado, quero fazer login com email/senha e ter minha sessão renovada automaticamente para que eu não precise reautenticar com frequência.

**Por que P1**: Base para acesso a todas as rotas protegidas.

**Acceptance Criteria**:

1. WHEN o usuário envia `POST /auth/login` com credenciais válidas THEN o sistema SHALL retornar `accessToken` (JWT, 15 min, em memória) e definir cookie `httpOnly + Secure + SameSite=Strict` com `refreshToken` (7 dias)
2. WHEN o usuário envia `POST /auth/login` com senha incorreta THEN o sistema SHALL retornar `401 Unauthorized`
3. WHEN o frontend detecta access token expirado THEN o sistema SHALL chamar `POST /auth/refresh` automaticamente e renovar o `accessToken` sem interrupção para o usuário
4. WHEN o `refreshToken` é inválido ou expirado THEN o sistema SHALL retornar `401` e o frontend SHALL redirecionar para login
5. WHEN o usuário acessa rota protegida sem token THEN o sistema SHALL retornar `401 Unauthorized`

**Independent Test**: Login → acesso a rota protegida → aguardar expiração → verificar renovação automática.

---

### P1: Recuperação de Senha — MVP

**User Story**: Como usuário que esqueceu a senha, quero redefinir minha senha usando minha chave de segurança para que eu recupere o acesso à minha conta.

**Por que P1**: Sem recuperação de senha, contas ficam permanentemente inacessíveis.

**Acceptance Criteria**:

1. WHEN o usuário envia `POST /auth/recover-password` com email, securityKey e newPassword válidos THEN o sistema SHALL redefinir a senha e retornar `{ success: true }`
2. WHEN a securityKey não corresponde ao hash no banco THEN o sistema SHALL retornar `403 Forbidden`
3. WHEN o email não existe THEN o sistema SHALL retornar `404 Not Found`

**Independent Test**: Cadastrar usuário → anotar securityKey → chamar recover-password → fazer login com nova senha.

---

### P1: Setup Inicial Obrigatório — MVP

**User Story**: Como usuário que acabou de se cadastrar, quero ser guiado para configurar meu perfil de Instagram antes de criar posts para que o sistema conheça minha identidade visual.

**Por que P1**: Sem o setup do perfil (`map-instagram-profile`), o worker de processamento não possui as diretrizes visuais e de comunicação para gerar posts consistentes.

**Acceptance Criteria**:

1. WHEN o usuário acessa a tela de criação sem a estrutura `map-instagram-profile` configurada THEN o sistema SHALL bloquear o acesso à interface de criação e exibir mensagem clara com o passo a passo do que deve ser feito
2. WHEN a estrutura `map-instagram-profile` está presente para o usuário THEN o sistema SHALL liberar o acesso completo à interface de criação
3. WHEN o sistema verifica o setup THEN a verificação SHALL ocorrer via endpoint protegido por JWT, com resultado isolado por `user_id`

**Independent Test**: Criar usuário sem setup → verificar bloqueio → configurar setup → verificar liberação.

---

### P1: Criação de Post (Single e Carrossel) — MVP

**User Story**: Como usuário com perfil configurado, quero escrever um prompt descrevendo o post que desejo e receber os slides gerados respeitando minha identidade visual para que eu possa baixá-los e publicar no Instagram.

**Por que P1**: É o core value proposition do produto.

**Acceptance Criteria**:

1. WHEN o usuário envia `POST /chats/:id/messages` com prompt válido THEN a API Go SHALL aceitar a mensagem, persistir a mensagem do usuário, criar um job e retornar **`202 Accepted`** com `jobId`; o serviço Python (LangGraph) SHALL executar o pipeline de geração (perfil → otimização → slides → renderização → S3) e notificar a API Go ao concluir; a API Go SHALL persistir a mensagem do assistente e os artefatos e expor o resultado via `GET /chats/:id` (e URLs assinadas para arquivos)
2. WHEN o usuário cria o 6º chat THEN o sistema SHALL remover automaticamente o chat mais antigo (incluindo seus arquivos no S3) antes de criar o novo
3. WHEN o setup inicial (`map-instagram-profile`) está ausente THEN o sistema SHALL retornar erro claro e não despachar o job
4. WHEN a OpenAI API está indisponível ou falha durante o processamento THEN o worker Python SHALL aplicar retry/backoff e marcar o job como falha com mensagem amigável; a API Go SHALL expor o status do job (`failed`) e o frontend SHALL poder consultá-lo
5. WHEN o Playwright/Chromium ou o pipeline de renderização falha no worker Python THEN o worker SHALL registrar o erro e notificar a API Go com falha; a API Go SHALL propagar o status `failed` do job (sem exigir que o Go execute Playwright)
6. WHEN o upload ao S3 falha no worker THEN o worker SHALL aplicar retry automático com backoff; se falhar após retries, o job SHALL falhar e o estado SHALL ser refletido na API Go
7. WHEN o sistema recebe input do usuário THEN a API Go SHALL sanitizar o conteúdo antes de despachar o job; o worker SHALL aplicar instruções restritivas no pipeline LLM para prevenção de prompt injection
8. WHEN a criação de job ou endpoints relacionados ao processamento excedem o rate limit por usuário THEN o sistema SHALL retornar `429 Too Many Requests`

**Independent Test**: Enviar prompt → receber `202` + `jobId` → após conclusão (polling de status ou `GET /chats/:id`) verificar JPEGs no S3 e `downloadUrl` → fazer download do arquivo.

---

### P1: Histórico de Posts — MVP

**User Story**: Como usuário, quero ver os últimos 5 posts que criei para que eu possa revisitá-los, baixá-los ou deletá-los.

**Por que P1**: Sem histórico, o usuário perde o acesso ao conteúdo gerado após fechar a sessão.

**Acceptance Criteria**:

1. WHEN o usuário acessa `GET /chats` THEN o sistema SHALL retornar os últimos 5 chats do usuário ordenados por `created_at DESC`
2. WHEN o usuário acessa `GET /chats/:id` THEN o sistema SHALL retornar o chat com todas as mensagens
3. WHEN o usuário acessa chat de outro usuário THEN o sistema SHALL retornar `403 Forbidden`
4. WHEN o usuário chama `DELETE /chats/:id` THEN o sistema SHALL remover o chat, suas mensagens e todos os arquivos associados no S3

**Independent Test**: Criar 3 chats → listar → verificar apenas os 3 → deletar 1 → verificar remoção no banco e S3.

---

### P1: Download de Arquivos — MVP

**User Story**: Como usuário, quero baixar os slides gerados (individualmente ou todos de uma vez em `.zip`) para que eu possa publicá-los no Instagram.

**Por que P1**: Sem download, o produto não entrega valor tangível ao usuário.

**Acceptance Criteria**:

1. WHEN o usuário acessa `GET /chats/:id/files/:fileId` THEN o sistema SHALL retornar o JPEG correto com `Content-Type: image/jpeg`
2. WHEN o usuário acessa `GET /chats/:id/files/download` THEN o sistema SHALL gerar e retornar um arquivo `.zip` com todos os JPEGs do chat
3. WHEN o arquivo solicitado não pertence ao usuário autenticado THEN o sistema SHALL retornar `403 Forbidden`
4. WHEN o arquivo não existe no S3 THEN o sistema SHALL retornar `404 Not Found`

**Independent Test**: Gerar post com 5 slides → download individual de cada slide → download do zip → verificar conteúdo.

---

### P2: Re-prompt (Refinamento de Post)

**User Story**: Como usuário, quero enviar uma mensagem de refinamento em um chat existente para que eu possa ajustar o post sem começar do zero.

**Por que P2**: Aumenta qualidade e produtividade, mas o fluxo principal já funciona sem re-prompt.

**Acceptance Criteria**:

1. WHEN o usuário envia nova mensagem em `POST /chats/:id/messages` em um chat existente THEN o sistema SHALL usar o resumo do chat (`chat_content_resume`) como contexto quando disponível, ou o histórico completo quando ausente
2. WHEN o novo conteúdo é gerado THEN o sistema SHALL salvar os novos arquivos no S3 e adicionar a nova mensagem ao histórico do chat
3. WHEN o re-prompt é processado THEN o sistema SHALL aplicar as mesmas validações de segurança e rate limiting do fluxo de criação inicial

**Independent Test**: Criar post → re-prompt com "torna os slides mais vibrantes" → verificar novo conjunto de JPEGs gerado.

---

### P2: Cron Job de Sumarização de Chats

**User Story**: Como sistema, quero sumarizar diariamente os chats com conteúdo novo para que o contexto enviado ao LLM em re-prompts seja compacto e de baixo custo.

**Por que P2**: Importante para controle de custo de tokens, mas o produto funciona sem isso no MVP inicial.

**Acceptance Criteria**:

1. WHEN o cron job roda THEN o sistema SHALL buscar todos os chats com `chat_content.created_at` mais recente que `chat_content_resume.summarized_at`
2. WHEN um chat elegível é encontrado THEN o sistema SHALL enviar o histórico completo para o GPT-5.4 Mini com instrução de sumarização compacta e salvar/atualizar o registro em `chat_content_resume`
3. WHEN um chat não possui conteúdo novo THEN o sistema SHALL ignorá-lo sem atualizar o resumo
4. WHEN o job excede 5 minutos de execução THEN o sistema SHALL emitir alerta de monitoramento

**Independent Test**: Criar chat com mensagens → rodar job manualmente → verificar registro em `chat_content_resume`.

---

## Edge Cases

- WHEN email enviado para `/auth/register` tem formato inválido THEN o sistema SHALL retornar `400 Bad Request`
- WHEN o payload de `POST /chats/:id/messages` excede o tamanho permitido THEN o sistema SHALL retornar `413 Payload Too Large`
- WHEN o usuário tenta acessar `/chats/:id` de chat deletado THEN o sistema SHALL retornar `404 Not Found`
- WHEN o Chromium não está instalado no ambiente do **worker Python** THEN o worker SHALL falhar o job com mensagem clara nos logs; a API Go SHALL expor status `failed` para esse job (a falha não é tratada como `503` síncrono na rota de mensagem, que já respondeu `202`)
- WHEN há mais de 20 tentativas de login falhas por IP em 5 minutos THEN o sistema SHALL bloquear temporariamente o IP
- WHEN o download de zip é solicitado para chat sem arquivos THEN o sistema SHALL retornar `404 Not Found`
- WHEN `POST /chats` é chamado e o usuário já tem 5 chats THEN o sistema SHALL deletar o mais antigo antes de criar o novo (sem erro para o usuário)

---

## Requirement Traceability

| Requirement ID | Story | Fase | Status |
|----------------|-------|------|--------|
| AUTH-01 | P1: Cadastro — geração e exibição da securityKey | Tasks | Pending |
| AUTH-02 | P1: Cadastro — validação de email duplicado | Tasks | Pending |
| AUTH-03 | P1: Cadastro — validação de senha | Tasks | Pending |
| AUTH-04 | P1: Login — JWT + cookie httpOnly | Tasks | Pending |
| AUTH-05 | P1: Login — credenciais inválidas | Tasks | Pending |
| AUTH-06 | P1: Renovação automática de access token | Tasks | Pending |
| AUTH-07 | P1: Rotas protegidas sem token → 401 | Tasks | Pending |
| AUTH-08 | P1: Recuperação de senha com securityKey | Tasks | Pending |
| AUTH-09 | P1: Recuperação — securityKey incorreta → 403 | Tasks | Pending |
| SETUP-01 | P1: Bloqueio de criação sem map-instagram-profile | Tasks | Pending |
| SETUP-02 | P1: Liberação com map-instagram-profile presente | Tasks | Pending |
| POST-01 | P1: Pipeline LangGraph: load_profile → optimize → generate_slides | Tasks | Pending |
| POST-02 | P1: Renderização JPEG no worker Python (Playwright) | Tasks | Pending |
| POST-03 | P1: Upload S3 + callback de conclusão ao Go | Tasks | Pending |
| POST-04 | P1: Remoção automática do chat mais antigo ao atingir limite | Tasks | Pending |
| POST-05 | P1: OpenAI indisponível — tratamento no worker; Go expõe status do job | Tasks | Pending |
| POST-06 | P1: Falha Playwright/render — worker; Go propaga status `failed` | Tasks | Pending |
| POST-07 | P1: Retry com backoff — falha no S3 (worker) | Tasks | Pending |
| POST-10 | P1: Contrato Go↔Python: jobId, idempotência, auth de serviço | Tasks | Pending |
| POST-11 | P1: Go: endpoint interno `POST /internal/jobs/:id/complete` | Tasks | Pending |
| POST-08 | P1: Sanitização de input + prevenção de prompt injection | Tasks | Pending |
| POST-09 | P1: Rate limiting por usuário para endpoints LLM | Tasks | Pending |
| HIST-01 | P1: Listagem dos últimos 5 chats | Tasks | Pending |
| HIST-02 | P1: Visualização do chat com mensagens | Tasks | Pending |
| HIST-03 | P1: Isolamento — acesso a chat de outro usuário → 403 | Tasks | Pending |
| HIST-04 | P1: Deleção de chat + S3 + mensagens | Tasks | Pending |
| FILE-01 | P1: Download de arquivo único (JPEG) | Tasks | Pending |
| FILE-02 | P1: Download de todos os arquivos (.zip) | Tasks | Pending |
| FILE-03 | P1: Isolamento — arquivo de outro usuário → 403 | Tasks | Pending |
| REPROMPT-01 | P2: Re-prompt com contexto de resumo | Tasks | Pending |
| REPROMPT-02 | P2: Persistência de novos arquivos no S3 | Tasks | Pending |
| CRON-01 | P2: Sumarização diária de chats elegíveis | Tasks | Pending |
| CRON-02 | P2: Ignorar chats sem conteúdo novo | Tasks | Pending |

**Cobertura:** 33 total, 33 mapeados para tasks, 0 unmapped

---

## Success Criteria

Como saber que o sistema está pronto para produção:

- [ ] Usuário consegue se cadastrar, configurar perfil e gerar o primeiro post em menos de 10 minutos
- [ ] Tempo de geração de post (p95) < 15 segundos
- [ ] Taxa de erro geral < 0,5%
- [ ] Latência da API (p95) < 500ms (excluindo chamadas ao LLM)
- [ ] 100% dos fluxos críticos cobertos por testes (auth, criação de post, download, histórico)
- [ ] Cobertura de testes unitários > 75%
- [ ] Nenhum dado de usuário acessível por outro usuário (zero vazamentos de isolamento)
- [ ] Deploy bem-sucedido em staging com smoke tests passando
