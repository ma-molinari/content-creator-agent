# Anexar Imagem ao Prompt — Tasks

**Design**: `.specs/features/attach-image-to-prompt/design.md`
**Spec**: `.specs/features/attach-image-to-prompt/spec.md`
**Status**: Draft

---

## Execution Plan

```
Phase 1 — DB Foundation (Sequential):
  T1 → T2

Phase 2 — Backend API (após T2)              Phase 2 — Worker (independente)
  T3 [P] CollectS3KeysForChat                  T10 [P] state.py
  T4 [P] CreateUserMessageAndJob ext           T11 [P] s3_image_utils
  T5 [P] DispatchPayload (Go)                  T12 [P] describe_user_attachments
  T6 [P] validateAndUploadAttachments          T13 [P] render allowlist
  T8 [P] refreshContentImageURLs ext           T14 [P] prompt generate_slides
  T9 [P] chatContentJSON ext                   T15 [P] prompt edit_slides
                                                T16 [P] attachment_block helper

Phase 3 — Sequencial / Integração:
  T6 → T7 (handler multipart)
  T10 → T17 (Worker DispatchPayload Pydantic)
  T12 + T17 → T18 (graph.py rewire)
  T16 → T19 (integrar em nós generate/edit/optimize)
  T9 → T20 (api/chats.ts types + postChatMessage)

Phase 4 — Frontend (após T20):
  T20 → T21 (ComposerBar)
  T20 → T22 (MessageBubbleUser)
  T20 + T21 → T23 (Chat page + ChatThread otimista)
  T23 → T24 (JobStatusIndicator P3, opcional)

Phase 5 — Integration tests:
  T7 + T18 → T25 (multipart end-to-end)
  T3 → T26 (delete cleanup)
```

---

## Parallel Execution Map

```
Phase 1 (Sequential):
  T1 ──→ T2

Phase 2 (Parallel — dois tracks):
  After T2 (Go API):                After nothing (Worker):
    ├─ T3 [P]                         T10 [P]
    ├─ T4 [P]                         T11 [P]
    ├─ T5 [P]                         T12 [P]   (depende de T10 + T11)
    ├─ T6 [P]                         T13 [P]
    ├─ T8 [P]                         T14 [P]
    └─ T9 [P]                         T15 [P]
                                       T16 [P]

Phase 3 (Sequential — gates):
  T6 ──→ T7
  T10 ──→ T17
  T12 + T17 ──→ T18
  T16 ──→ T19
  T9 ──→ T20

Phase 4 (Frontend):
  T20 ──→ T21
  T20 ──→ T22
  T21 + T22 ──→ T23
  T23 ──→ T24 (P3, opcional)

Phase 5 (Tests):
  T7 + T18 ──→ T25
  T3 ──→ T26

Critical path: T1 → T2 → T6 → T7 → T20 → T21 → T23 → T25
Total tasks: 26 (24 obrigatórias + 2 opcionais) | Parallelizáveis: 13 | Phases: 5
```

---

## Task Breakdown

### T1: Migration SQL 013 — `chat_content_attachment`

**What**: Criar par de migrations para a tabela `chat_content_attachment` com FK cascade.
**Where**:
- `apps/api/internal/db/migrations/013_chat_content_attachment.up.sql`
- `apps/api/internal/db/migrations/013_chat_content_attachment.down.sql`

**Depends on**: Nenhum
**Reuses**: Padrão de migrations 011/012 (PK uuid + cascade FK + índice).
**Requirement**: AIP-04, AIP-07

**Done when**:
- [ ] `up.sql`: cria tabela com colunas `id, chat_content_id, s3_key (varchar 512), mime_type (varchar 64), size_bytes (bigint), sort_order (int), created_at (timestamptz)` + FK `ON DELETE CASCADE` + índice em `chat_content_id`.
- [ ] `down.sql`: drop do índice e da tabela com `IF EXISTS`.
- [ ] Numeração `013_` seguindo a sequência atual.

**Verify**:
```bash
ls apps/api/internal/db/migrations/ | grep 013
```

**Commit**: `feat(db): add chat_content_attachment table`

---

### T2: Model GORM — `ChatContentAttachment` + relação em `ChatContent`

**What**: Adicionar struct `ChatContentAttachment` em `models.go` com tags GORM, e adicionar `Attachments []ChatContentAttachment` ao struct `ChatContent`.
**Where**: `apps/api/internal/db/models.go`
**Depends on**: T1
**Reuses**: Padrão `ChatContentImage` (mesmo arquivo).
**Requirement**: AIP-04

**Done when**:
- [ ] `ChatContentAttachment` definido com todos os campos da migration + tags GORM corretas + campo `URL string \`gorm:"-"\`` (derivado).
- [ ] `func (ChatContentAttachment) TableName() string { return "chat_content_attachment" }`.
- [ ] `ChatContent` ganha `Attachments []ChatContentAttachment \`gorm:"foreignKey:ChatContentID"\``.
- [ ] `go build ./...` passa sem erros.

**Verify**:
```bash
cd apps/api && go build ./...
```

**Commit**: `feat(db): add ChatContentAttachment model and relation`

---

### T3: Repository — estender `CollectS3KeysForChat` [P]

**What**: Estender `CollectS3KeysForChat` para incluir também as chaves S3 da tabela `chat_content_attachment`.
**Where**: `apps/api/internal/chat/repository.go`
**Depends on**: T2
**Reuses**: Lógica atual de UNION entre `s3_key` (JPEG) e `html_s3_key` (HTML).
**Requirement**: AIP-07

**Done when**:
- [ ] Nova query coleta `s3_key` de `chat_content_attachment` cujos `chat_content_id` pertencem ao chat (subquery na `chat_content`).
- [ ] Resultado faz dedup com `s3_key` e `html_s3_key` no mesmo `seen` map já existente.
- [ ] Ordem dos retornos não importa para o `DeleteMany`, mas mantém estabilidade.
- [ ] `go build ./...` + testes existentes passam.

**Verify**:
```bash
cd apps/api && go test ./internal/chat/...
```

**Commit**: `feat(chat): include user attachments in CollectS3KeysForChat`

---

### T4: Repository — estender `CreateUserMessageAndJob` para anexos [P]

**What**: Adicionar parâmetro de attachments à transação que cria `ChatContent` + `Job` para também inserir `chat_content_attachment` no mesmo `tx`.
**Where**: `apps/api/internal/chat/repository.go`
**Depends on**: T2
**Reuses**: Transação atual com `db.Transaction(...)`.
**Requirement**: AIP-04

**Done when**:
- [ ] Assinatura nova: `CreateUserMessageAndJob(ctx, msg *db.ChatContent, job *db.Job, setTitle *string, attachments []db.ChatContentAttachment) error` (ou método separado `CreateUserMessageAndJobWithAttachments` mantendo retrocompat se preferir).
- [ ] Cada `ChatContentAttachment.ChatContentID` é populado com `msg.ID` antes do insert.
- [ ] Insert dos anexos acontece dentro da mesma transação; rollback automático em qualquer falha.
- [ ] Caller existente (`PostMessage` sem attachments) passa slice vazio sem regressão.
- [ ] `go build ./...` + `go test ./internal/chat/...` passam.

**Verify**:
```bash
cd apps/api && go test ./internal/chat/...
```

**Commit**: `feat(chat): persist attachments in CreateUserMessageAndJob transaction`

---

### T5: `DispatchPayload` (Go) — campo `UserAttachmentS3Keys` [P]

**What**: Adicionar campo `UserAttachmentS3Keys []string` ao struct `DispatchPayload`.
**Where**: `apps/api/internal/jobs/worker_client.go`
**Depends on**: Nenhum
**Reuses**: Padrão `omitempty` de `ReferenceS3Keys` e `ExistingSlideHTMLKeys`.
**Requirement**: AIP-05

**Done when**:
- [ ] Campo adicionado: `UserAttachmentS3Keys []string \`json:"user_attachment_s3_keys,omitempty"\``.
- [ ] Não quebra nenhum `DispatchPayload{}` existente (slice nil → omitido na serialização).
- [ ] `go build ./...` passa.

**Verify**:
```bash
cd apps/api && go build ./...
```

**Commit**: `feat(jobs): add UserAttachmentS3Keys to DispatchPayload`

---

### T6: Service — `validateAndUploadAttachments` helper [P]

**What**: Novo método em `chat.Service` (ou helper privado em `post_message.go`) que recebe slice de inputs, valida, faz upload S3 paralelo e retorna keys + rollback handler.
**Where**: `apps/api/internal/chat/post_message.go` (método privado em `Service`)
**Depends on**: Nenhum (não toca DB)
**Reuses**: Lógica de `profile.UploadReferenceImage` (mime sniff, ext mapping, key UUID); padrão de errgroup.
**Requirement**: AIP-02, AIP-03

**Done when**:
- [ ] Definidos os sentinels: `ErrAttachmentTooLarge`, `ErrAttachmentInvalidType`, `ErrTooManyAttachments`, `ErrAttachmentUploadFailed` (no mesmo `service.go` com os demais).
- [ ] Constantes: `maxAttachmentBytes = 5 * 1024 * 1024`, `maxAttachmentsPerMessage = 4`, `allowedAttachmentMimes = {"image/jpeg","image/png","image/webp"}`.
- [ ] Função: `validateAndUploadAttachments(ctx, userID uuid.UUID, inputs []AttachmentInput) (keys []string, attachments []db.ChatContentAttachment, err error)`.
- [ ] Valida: `len(inputs) <= 4`; cada input `<= 5MB`; mime sniff via `http.DetectContentType` está no allowlist.
- [ ] Upload paralelo via `errgroup.WithContext`; key: `users/<userID>/chat-attachments/<uuid>.<ext>`.
- [ ] Em qualquer erro de upload: faz best-effort `store.Delete` para keys já uploadadas; retorna `ErrAttachmentUploadFailed`.
- [ ] Sucesso: retorna keys (na ordem dos inputs) + slice `db.ChatContentAttachment` (com `S3Key`, `MimeType`, `SizeBytes`, `SortOrder`).
- [ ] `go build ./...` passa.

**Verify**:
```bash
cd apps/api && go build ./...
```

**Commit**: `feat(chat): add validateAndUploadAttachments helper`

---

### T7: Handler — `PostMessage` aceitar multipart

**What**: Estender `Handler.PostMessage` para detectar `multipart/form-data` e extrair `content` + `attachments[]`; chamar service estendido; mapear novos sentinels para HTTP.
**Where**: `apps/api/internal/chat/handler.go` + `apps/api/internal/chat/post_message.go` (extensão do método `PostMessage` no service para aceitar `attachments []AttachmentInput` opcional)
**Depends on**: T4, T5, T6
**Reuses**: Padrão multipart de `profile.PostReference`; `mapChatErr`.
**Requirement**: AIP-01, AIP-03

**Done when**:
- [ ] Handler detecta `Content-Type: multipart/form-data`:
  - Parse `c.MultipartForm()`; extrai `c.FormValue("content")` para texto.
  - Extrai files com nome `attachments` (lê bytes via `io.LimitReader` por arquivo, máx 5MB+1).
  - Constrói `[]AttachmentInput{Data, MimeType (do header), SizeBytes, SortOrder}`.
- [ ] Caso JSON (compatibilidade): mantém binding atual; passa `nil` ao service.
- [ ] `Service.PostMessage` ganha parâmetro `attachments []AttachmentInput` (`nil`/`empty` mantém comportamento atual).
- [ ] `PostMessage` chama `validateAndUploadAttachments` ANTES de `CreateUserMessageAndJob`; em erro, retorna direto (sem persistir mensagem).
- [ ] Após upload OK: passa `attachments` (com `ChatContentID` zero, será preenchido) para `CreateUserMessageAndJob`; popula `UserAttachmentS3Keys: keys` no `DispatchPayload`.
- [ ] Em erro de dispatch após upload: NÃO faz rollback dos anexos no S3 (a mensagem ficou criada e o usuário verá o `Job{failed}` — anexos serão limpos no eventual delete do chat).
- [ ] Mapeamento de erros no handler: `ErrAttachmentTooLarge` → 413; `ErrAttachmentInvalidType` / `ErrTooManyAttachments` → 400; `ErrAttachmentUploadFailed` → 502.
- [ ] `go build ./...` + `go test ./internal/chat/...` passam.

**Verify**:
```bash
cd apps/api && go test ./internal/chat/...
```

**Commit**: `feat(chat): accept multipart attachments on POST /chats/:id/messages`

---

### T8: Service — `refreshContentImageURLs` inclui attachments [P]

**What**: Estender `refreshContentImageURLs` para gerar signed URLs também para `Contents[i].Attachments[j]`.
**Where**: `apps/api/internal/chat/service.go`
**Depends on**: T2
**Reuses**: `store.GetSignedURL`, `signedURLExpiry`.
**Requirement**: AIP-04

**Done when**:
- [ ] Novo loop dentro do método itera `Attachments` e popula `URL` em cada um.
- [ ] Falha de signing em qualquer attachment retorna o erro (mesmo padrão de Images).
- [ ] `go build ./...` + `go test ./internal/chat/...` passam.

**Verify**:
```bash
cd apps/api && go test ./internal/chat/...
```

**Commit**: `feat(chat): refresh signed URLs for user attachments`

---

### T9: Handler — `chatContentJSON` expõe `attachments` [P]

**What**: Adicionar campo `attachments` em `chatContentJSON` e popular em `chatToJSON`.
**Where**: `apps/api/internal/chat/handler.go`
**Depends on**: T2
**Reuses**: Padrão de `chatContentImgJSON` no mesmo arquivo.
**Requirement**: AIP-04

**Done when**:
- [ ] Definido `chatContentAttachJSON { ID uuid, URL string, MimeType string, SortOrder int }`.
- [ ] `chatContentJSON.Attachments []chatContentAttachJSON \`json:"attachments,omitempty"\``.
- [ ] `chatToJSON` itera `row.Attachments` e popula a slice (ordenada por `SortOrder`).
- [ ] Repository `GetByIDWithContents` (ou equivalente) faz Preload de `Attachments` (verificar se o Preload atual de `Images` cobre — pode precisar adicionar).
- [ ] `go build ./...` + `go test ./internal/chat/...` passam.

**Verify**:
```bash
cd apps/api && go test ./internal/chat/...
```

**Commit**: `feat(chat): expose attachments in chat JSON response`

---

### T10: Worker `state.py` — novos campos [P]

**What**: Adicionar 4 novos campos `NotRequired` ao `AgentState` para anexos do usuário.
**Where**: `apps/worker/app/state.py`
**Depends on**: Nenhum
**Reuses**: Padrão `NotRequired` no mesmo arquivo.
**Requirement**: AIP-05, AIP-06

**Done when**:
- [ ] `user_attachment_s3_keys: NotRequired[list[str]]`
- [ ] `user_attachment_descriptions: NotRequired[list[str]]`
- [ ] `user_attachment_intent: NotRequired[str]`
- [ ] `user_attachment_signed_urls: NotRequired[list[str]]`
- [ ] `python -c "from app.state import AgentState"` sem erros.

**Verify**:
```bash
cd apps/worker && python -c "from app.state import AgentState; print('ok')"
```

**Commit**: `feat(worker): add user attachment fields to AgentState`

---

### T11: Worker — `app/s3_image_utils.py` (promover utilities) [P]

**What**: Criar módulo compartilhado com `_fetch_bytes_limited`, `_guess_mime` (promover do `describe_references`) e nova função `presign_get_url(client, bucket, key, expires_in_seconds=3600)`.
**Where**: `apps/worker/app/s3_image_utils.py` (novo) + refactor mínimo de `apps/worker/app/nodes/describe_references.py` para importar do novo módulo.
**Depends on**: Nenhum
**Reuses**: Implementação atual de `_fetch_bytes_limited` e `_guess_mime`.
**Requirement**: AIP-05

**Done when**:
- [ ] `app/s3_image_utils.py` exporta: `fetch_bytes_limited`, `guess_mime`, `presign_get_url` (públicos sem underscore).
- [ ] `describe_references.py` importa do novo módulo (sem mudança de comportamento).
- [ ] `presign_get_url` usa `boto3` `generate_presigned_url('get_object', ...)`.
- [ ] `python -c "from app.s3_image_utils import fetch_bytes_limited, guess_mime, presign_get_url"` sem erros.
- [ ] `python -m pytest tests/` passa (testes existentes do `describe_references` continuam OK).

**Verify**:
```bash
cd apps/worker && python -m pytest tests/ -q
```

**Commit**: `refactor(worker): extract S3 image utilities to shared module`

---

### T12: Worker — `describe_user_attachments` nó + prompt [P]

**What**: Criar novo nó LangGraph `describe_user_attachments` que: (a) gera URLs presignadas, (b) descreve cada imagem via vision LLM, (c) classifica intenção (`explicit` vs `cover_default`).
**Where**:
- `apps/worker/app/nodes/describe_user_attachments.py`
- `apps/worker/prompts/describe_user_attachments.md`
**Depends on**: T10, T11
**Reuses**: Padrão completo de `describe_references.py` (S3 fetch paralelo + vision LLM + erros graceful); `s3_image_utils` de T11.
**Requirement**: AIP-05, AIP-06

**Done when**:
- [ ] `describe_user_attachments.md`: prompt de visão pedindo descrição curta (≤ 80 palavras) por imagem: tipo (foto/ilustração/screenshot/ícone), elementos principais, paleta dominante, estilo. Saída como lista numerada.
- [ ] `describe_user_attachments(state) -> dict` async:
  - Se `user_attachment_s3_keys` vazio → retorna `{}` (no-op).
  - Para cada key: gera presigned URL (1h) via `presign_get_url`.
  - Em paralelo: fetch bytes (`fetch_bytes_limited`) + envia ao vision LLM em uma única chamada com múltiplos blocos `image_url` data: base64.
  - Parseia resposta em lista de descrições alinhadas por índice.
  - Heurística de intenção: regex `re.compile(r"\b(use|usa|coloque|ponha|adicion[ea]|inclu[ai]|no\s+slide\s+\d+|como\s+(capa|fundo|hero|background)|na\s+capa|primeir[oa]\s+slide)\b", re.IGNORECASE)` em `state["raw_message"]`. Match → `"explicit"`, senão → `"cover_default"`.
  - Retorna `{user_attachment_descriptions, user_attachment_intent, user_attachment_signed_urls}`.
- [ ] Falhas (S3 ou LLM) → log + degradação segura (descrições vazias ou ausentes; URLs populadas se possível; intent mantém heurística).
- [ ] `python -c "from app.nodes.describe_user_attachments import describe_user_attachments"` sem erros.

**Verify**:
```bash
cd apps/worker && python -c "from app.nodes.describe_user_attachments import describe_user_attachments; print('ok')"
```

**Commit**: `feat(worker): add describe_user_attachments node`

---

### T13: Worker — `render_to_jpeg` allowlist S3 [P]

**What**: Estender `_allow_slide_route` em `render_to_jpeg.py` para permitir hosts S3 do bucket configurado (além de `data:` e Google Fonts).
**Where**: `apps/worker/app/nodes/render_to_jpeg.py`
**Depends on**: Nenhum
**Reuses**: `get_settings`, padrão atual de `_allow_slide_route`.
**Requirement**: AIP-06

**Done when**:
- [ ] Novo set de hosts permitidos calculado a partir de `settings.aws_s3_bucket` e `settings.aws_region`:
  - `<bucket>.s3.<region>.amazonaws.com`
  - `<bucket>.s3.amazonaws.com`
  - `s3.<region>.amazonaws.com`
- [ ] `_allow_slide_route` parseia `urlparse(url).hostname` e libera quando hostname está no set.
- [ ] Set é construído uma vez (lazy/module-level cache) — não re-cria por request.
- [ ] Testes existentes do `render_to_jpeg` (se houver) continuam passando.
- [ ] `python -c "from app.nodes.render_to_jpeg import render_to_jpeg"` sem erros.

**Verify**:
```bash
cd apps/worker && python -c "from app.nodes.render_to_jpeg import render_to_jpeg; print('ok')"
```

**Commit**: `feat(worker): allow S3 bucket hosts in Playwright route allowlist`

---

### T14: Prompt `generate_slides.md` — bloco de orientação para anexos [P]

**What**: Adicionar seção em `generate_slides.md` que ensina o LLM a usar `<anexos_do_usuario>` quando presente, com regras explícitas para `intent=cover_default` (img/background no slide 1) e `intent=explicit` (siga o prompt do usuário).
**Where**: `apps/worker/prompts/generate_slides.md`
**Depends on**: Nenhum
**Reuses**: Estrutura atual do prompt.
**Requirement**: AIP-05, AIP-06

**Done when**:
- [ ] Nova seção delimitada (ex.: `## ANEXOS_DO_USUARIO`) explicando:
  - Quando `<anexos_do_usuario>` aparece, cada `<imagem>` tem `n`, `url`, `mime` e descrição.
  - `intent="cover_default"` → IMAGEM 1 vira visual dominante do slide 1 (capa); demais imagens são apoio em slides intermediários ou ignoradas.
  - `intent="explicit"` → seguir estritamente a instrução do usuário em `<raw_message>`.
  - **SEMPRE** referenciar via URL completa em `src=` ou `background-image: url(...)`.
  - **NUNCA** omitir a tag `<img>` ou background quando `intent` exige uso.
- [ ] Bloco está consistente com restrições existentes (sem JS, sem URLs remotas além das anexadas/Google Fonts).

**Verify**:
```bash
grep -i "anexos_do_usuario" apps/worker/prompts/generate_slides.md | head -3
```

**Commit**: `feat(worker): add user attachments guidance to generate_slides prompt`

---

### T15: Prompt `edit_slides.md` — bloco de orientação para anexos [P]

**What**: Espelhar a seção de anexos no prompt de edição, com regra adicional: em refinamento sem instrução, atualizar slide 1 (capa) para incorporar a nova imagem; preservar demais slides.
**Where**: `apps/worker/prompts/edit_slides.md`
**Depends on**: Nenhum
**Reuses**: Estrutura atual + paralelo com T14.
**Requirement**: AIP-08

**Done when**:
- [ ] Nova seção `## ANEXOS_DO_USUARIO` com mesmas regras de uso do generate_slides.
- [ ] Regra extra: em `intent="cover_default"` durante edição, **substituir o visual dominante do slide 1** preservando texto/identidade dos slides 2+.
- [ ] Bloco consistente com restrições de design e formato `###SLIDE_FILE: ...`.

**Verify**:
```bash
grep -i "anexos_do_usuario" apps/worker/prompts/edit_slides.md | head -3
```

**Commit**: `feat(worker): add user attachments guidance to edit_slides prompt`

---

### T16: Worker — `app/attachment_block.py` helper [P]

**What**: Criar helper que formata o bloco `<anexos_do_usuario count="..." intent="...">` em texto pronto para concatenar no `user_content` dos nós LLM.
**Where**: `apps/worker/app/attachment_block.py`
**Depends on**: T10
**Reuses**: Tipos de `AgentState`.
**Requirement**: AIP-05, AIP-06, AIP-08

**Done when**:
- [ ] `format_user_attachments_block(state: AgentState) -> str` retorna `""` quando `user_attachment_s3_keys` vazio; senão monta string XML-like com `<imagem n=... url=... mime=...>descrição</imagem>` por anexo + bloco `ORIENTAÇÃO DE USO` resumindo intent.
- [ ] Tag de abertura inclui `count` e `intent`.
- [ ] Quando descrição estiver ausente para um índice, ainda monta `<imagem>` com URL e mime (texto vazio).
- [ ] Função pura (sem I/O), totalmente testável.
- [ ] `python -c "from app.attachment_block import format_user_attachments_block"` sem erros.

**Verify**:
```bash
cd apps/worker && python -c "from app.attachment_block import format_user_attachments_block; print('ok')"
```

**Commit**: `feat(worker): add attachment_block helper to format user attachments for prompts`

---

### T17: Worker `main.py` — `DispatchPayload` Pydantic + `_initial_state`

**What**: Estender `DispatchPayload` Pydantic com `user_attachment_s3_keys` e popular o estado inicial.
**Where**: `apps/worker/app/main.py`
**Depends on**: T10
**Reuses**: Padrão de `reference_s3_keys` e `existing_slide_html_s3_keys`.
**Requirement**: AIP-05

**Done when**:
- [ ] `DispatchPayload` ganha `user_attachment_s3_keys: list[str] | None = None`.
- [ ] `_initial_state` popula `user_attachment_s3_keys: list(payload.user_attachment_s3_keys or [])`.
- [ ] `python -c "from app.main import DispatchPayload"` sem erros.
- [ ] Testes existentes do worker (se houver) continuam passando.

**Verify**:
```bash
cd apps/worker && python -m pytest tests/ -q
```

**Commit**: `feat(worker): accept user_attachment_s3_keys in DispatchPayload`

---

### T18: Worker `graph.py` — inserir `describe_user_attachments`

**What**: Adicionar `describe_user_attachments` como nó entre `describe_references` e `detect_intent` no grafo.
**Where**: `apps/worker/app/graph.py`
**Depends on**: T12, T17
**Reuses**: Padrão `add_node` + `add_edge` existente.
**Requirement**: AIP-05

**Done when**:
- [ ] Import + `add_node("describe_user_attachments", describe_user_attachments)`.
- [ ] Substituir `add_edge("describe_references", "detect_intent")` por:
  - `add_edge("describe_references", "describe_user_attachments")`
  - `add_edge("describe_user_attachments", "detect_intent")`
- [ ] `python -c "from app.graph import graph; print(sorted(graph.nodes))"` mostra `describe_user_attachments` na lista.

**Verify**:
```bash
cd apps/worker && python -c "from app.graph import graph; print('describe_user_attachments' in graph.nodes)"
```

**Commit**: `feat(worker): wire describe_user_attachments into graph`

---

### T19: Worker — integrar `attachment_block` em `generate_slides`, `edit_slides`, `optimize_prompt`

**What**: Em cada nó relevante, chamar `format_user_attachments_block(state)` e concatenar (não-vazio) ao `user_content` antes da chamada LLM.
**Where**:
- `apps/worker/app/nodes/generate_slides.py`
- `apps/worker/app/nodes/edit_slides.py`
- `apps/worker/app/nodes/optimize_prompt.py`
**Depends on**: T16
**Reuses**: `format_user_attachments_block`; estrutura atual de `user_content`.
**Requirement**: AIP-05, AIP-06, AIP-08

**Done when**:
- [ ] Nos 3 nós: `block = format_user_attachments_block(state); if block: user_content += "\n\n" + block`.
- [ ] Posição: depois do `<raw_message>` ou contexto principal, antes de "ORIENTAÇÃO".
- [ ] Não quebra mensagens sem anexos (block é string vazia → não concatena).
- [ ] `python -c "from app.nodes.generate_slides import generate_slides; from app.nodes.edit_slides import edit_slides; from app.nodes.optimize_prompt import optimize_prompt"` sem erros.

**Verify**:
```bash
cd apps/worker && python -c "from app.nodes.generate_slides import generate_slides; from app.nodes.edit_slides import edit_slides; from app.nodes.optimize_prompt import optimize_prompt; print('ok')"
```

**Commit**: `feat(worker): inject user attachments block into LLM nodes`

---

### T20: `api/chats.ts` — types + `postChatMessage` multipart

**What**: Adicionar tipo `ChatContentAttachment`, estender `ChatContent` com `attachments?`, criar/estender `postChatMessage(chatId, content, attachments?)` para usar `FormData` quando há anexos.
**Where**: `apps/web/src/api/chats.ts`
**Depends on**: T9
**Reuses**: `api` axios client; padrão de tipos no mesmo arquivo.
**Requirement**: AIP-03, AIP-04

**Done when**:
- [ ] `ChatContentAttachment = { id, url, mimeType, sortOrder }`.
- [ ] `ChatContent.attachments?: ChatContentAttachment[]`.
- [ ] `postChatMessage(chatId: string, content: string, attachments?: File[]): Promise<{ jobId: string }>`:
  - Sem `attachments` ou vazio → POST JSON atual.
  - Com `attachments` → `FormData` com `content` (string) + cada arquivo em `attachments` (mesma chave repetida).
  - Axios infere `Content-Type: multipart/form-data` automaticamente quando recebe `FormData`.
- [ ] `npm run build` (web) sem erros TypeScript.

**Verify**:
```bash
cd apps/web && npm run build 2>&1 | grep -E "error|Error" | head -10
```

**Commit**: `feat(web/api): support multipart attachments in postChatMessage`

---

### T21: `ComposerBar` — botão de anexar + thumbnails + state

**What**: Adicionar botão de clipe ao `ComposerBar`, state de arquivos, validação client-side, thumbnails inline com remover, e mudar assinatura de `onSend`.
**Where**: `apps/web/src/components/composer/ComposerBar.tsx`
**Depends on**: T20
**Reuses**: `useState`/`useRef`; `URL.createObjectURL`; `toast` (`lib/toast`).
**Requirement**: AIP-01, AIP-02, AIP-03

**Done when**:
- [ ] Novo state: `attachments: { id: string; file: File; previewUrl: string }[]`.
- [ ] Constantes: `MAX_ATTACHMENTS = 4`, `MAX_BYTES = 5 * 1024 * 1024`, `ALLOWED_MIMES = ['image/jpeg','image/png','image/webp']`.
- [ ] Botão `IconPaperclip` à esquerda do textarea (criar/usar ícone existente em `ui/action-icons` se disponível).
- [ ] Click no botão → `<input type="file" accept="image/jpeg,image/png,image/webp" multiple hidden ref={fileInputRef} onChange={...}>`.
- [ ] `onChange` valida arquivo a arquivo: rejeita por mime/size, calcula slots restantes (4 − atuais), aceita só os que cabem; toast com motivo dos rejeitados.
- [ ] Grid horizontal de thumbnails ACIMA do textarea (inside the bordered box) com cada thumb mostrando preview + botão **×** (`IconClose`/`IconX`).
- [ ] Remover thumb chama `URL.revokeObjectURL`.
- [ ] `onSend` agora `(text: string, files: File[]) => Promise<void>`.
- [ ] Em sucesso: limpar `attachments` + revogar todas as previews. Em erro: preservar (no-op).
- [ ] `useEffect` cleanup ao desmontar revoga todas as previews.
- [ ] `npm run build` sem erros.

**Verify**:
```bash
cd apps/web && npm run build 2>&1 | grep -E "error|Error" | head -10
```

**Commit**: `feat(web/composer): add image attachment support to ComposerBar`

---

### T22: `MessageBubbleUser` — renderizar thumbnails de anexos

**What**: Estender `MessageBubbleUser` para receber `attachments?` e renderizar thumbnails clicáveis com lightbox simples.
**Where**: `apps/web/src/components/chat/MessageBubbleUser.tsx`
**Depends on**: T20
**Reuses**: Padrão visual de `SlideViewer`; tokens CSS do projeto; `IconClose` para fechar lightbox.
**Requirement**: AIP-04

**Done when**:
- [ ] Prop nova: `attachments?: ChatContentAttachment[]`.
- [ ] Render condicional: se `attachments?.length > 0`, grid horizontal acima do texto com thumbnails (aspect ratio preservado, max-height razoável).
- [ ] Click em thumbnail abre lightbox modal (overlay escuro + imagem grande + botão fechar + `Esc` para fechar).
- [ ] `<img onError={...}>` mostra placeholder quando URL falha (texto + ícone "imagem indisponível").
- [ ] A11y: `alt` por imagem ("Anexo N de M"), botão fechar com `aria-label`.
- [ ] `npm run build` sem erros.

**Verify**:
```bash
cd apps/web && npm run build 2>&1 | grep -E "error|Error" | head -10
```

**Commit**: `feat(web/chat): render user attachments inside message bubble`

---

### T23: `Chat.tsx` + `ChatThread.tsx` — passar files no envio + bolha otimista com previews

**What**: Atualizar a página `Chat` para passar `files` do `ComposerBar` ao `postChatMessage` e ao state otimista, e atualizar `ChatThread` para renderizar a bolha pendente com thumbnails (object URLs locais até o GET trazer do servidor).
**Where**:
- `apps/web/src/pages/Chat.tsx`
- `apps/web/src/components/chat/ChatThread.tsx`
**Depends on**: T21, T22
**Reuses**: Padrão atual de `pendingText`, `serverUserMessageCoversPending`, `MessageBubbleUser`.
**Requirement**: AIP-03, AIP-04

**Done when**:
- [ ] `Chat.tsx`: handler de `onSend` recebe `(text, files)`, gera object URLs locais para `files` (preview otimista), salva em state `pendingAttachments`, chama `postChatMessage(chatId, text, files)`.
- [ ] Após sucesso: limpa `pendingAttachments` (e revoga URLs) quando o GET retorna a `ChatContent` correspondente do servidor.
- [ ] `ChatThread`: aceita `pendingAttachments?: { id, url, mimeType }[]` e renderiza na bolha `MessageBubbleUser` pendente.
- [ ] Bolhas do servidor (`MessageBubbleUser` mapeado de `chat.contents`) recebem `attachments={msg.attachments}` quando role=user.
- [ ] Sem regressão para mensagens só-texto.
- [ ] `npm run build` sem erros.

**Verify**:
```bash
cd apps/web && npm run build 2>&1 | grep -E "error|Error" | head -10
```

**Commit**: `feat(web/chat): wire user attachments through Chat page and ChatThread`

---

### T24: `JobStatusIndicator` — label adicional para anexos (P3, opcional)

**What**: Quando o job em andamento tem anexos, mostrar label "Aplicando imagens anexadas…" no `JobStatusIndicator` durante `processing`.
**Where**: `apps/web/src/components/chat/JobStatusIndicator.tsx` (e callers)
**Depends on**: T23
**Reuses**: Componente atual.
**Requirement**: AIP-09

**Done when**:
- [ ] Nova prop `hasUserAttachments?: boolean`.
- [ ] Quando `status === 'processing'` e `hasUserAttachments`, label vira "Aplicando imagens anexadas…".
- [ ] Caller (`ChatThread` ou `Chat.tsx`) passa `true` quando o último user message tem `attachments?.length > 0` ou quando `pendingAttachments?.length > 0`.
- [ ] `npm run build` sem erros.

**Verify**:
```bash
cd apps/web && npm run build 2>&1 | grep -E "error|Error" | head -10
```

**Commit**: `feat(web/chat): add attachment-aware label to JobStatusIndicator`

---

### T25: Integration test — multipart end-to-end

**What**: Teste de integração Go que exercita `POST /chats/:id/messages` com `multipart/form-data` (texto + 2 arquivos), valida persistência, payload despachado ao mock worker, e callback de sucesso.
**Where**: `apps/api/integration/attachments_test.go` (novo, com tag `integration`)
**Depends on**: T7, T18
**Reuses**: `helpers_test.go` (mock worker, perfil, S3 mock); padrão de `failure_test.go` e `chat_crud_test.go`.
**Requirement**: AIP-03, AIP-04, AIP-05

**Done when**:
- [ ] Caso 1: 2 arquivos PNG válidos (1KB cada de bytes válidos PNG header) + texto → 202 + `jobId`; verifica:
  - `chat_content` foi criado com role=user.
  - `chat_content_attachment` tem 2 linhas com `s3_key` populado.
  - Mock worker recebeu `user_attachment_s3_keys` no payload com 2 keys.
  - Mock S3 contém os 2 objetos.
- [ ] Caso 2: 5º anexo rejeitado (5 arquivos no form) → 400 com mensagem clara.
- [ ] Caso 3: arquivo > 5MB rejeitado → 413.
- [ ] Caso 4: arquivo `text/plain` enviado como `attachments` → 400 (sniff detecta).
- [ ] Caso 5: erro no upload S3 (mock que falha no 1º arquivo) → 502 + nenhum `ChatContent` ou `Job` criado no DB.
- [ ] `make test-integration` passa.

**Verify**:
```bash
cd apps/api && make test-integration
```

**Commit**: `test(integration): add end-to-end coverage for multipart attachments`

---

### T26: Integration test — DELETE chat com anexos limpa S3

**What**: Teste de integração que cria chat, envia mensagem com anexos, deleta chat e valida que o mock S3 não tem mais as keys dos anexos.
**Where**: `apps/api/integration/attachments_test.go` (mesmo arquivo da T25, ou separado)
**Depends on**: T3
**Reuses**: Mock worker e S3 da `helpers_test.go`.
**Requirement**: AIP-07

**Done when**:
- [ ] Cria chat → posta mensagem com 2 anexos → simula callback do worker (mock) marcando job done com 1 artefato slide → `DELETE /chats/:id` → 204.
- [ ] Verifica no mock S3: as 2 keys de anexo + a key do slide foram passadas ao `DeleteMany`.
- [ ] Verifica no DB: `chat`, `chat_content`, `chat_content_attachment`, `chat_content_image`, `jobs` foram deletados (cascade).
- [ ] Caso adicional: criar 6º chat (eviction) também limpa anexos do chat evictado.
- [ ] `make test-integration` passa.

**Verify**:
```bash
cd apps/api && make test-integration
```

**Commit**: `test(integration): verify S3 cleanup of user attachments on chat delete and eviction`

---

## Requirement Traceability

| Requirement ID | Tasks |
| -------------- | ------------------------------------ |
| AIP-01         | T7, T21                              |
| AIP-02         | T6, T21                              |
| AIP-03         | T6, T7, T20, T21, T23, T25           |
| AIP-04         | T1, T2, T8, T9, T20, T22, T23, T25   |
| AIP-05         | T5, T10, T11, T12, T16, T17, T18, T19, T25 |
| AIP-06         | T10, T12, T13, T14, T16, T19         |
| AIP-07         | T3, T26                              |
| AIP-08         | T15, T19                             |
| AIP-09         | T24                                  |

**Coverage:** 9 requirements → 26 tasks mapeados.

---

## Granularity Check

| Task | Escopo | Status |
| ---- | ------ | ------ |
| T1: Migration SQL up/down | 2 arquivos (par) | ✅ Granular |
| T2: Model GORM + relação | 1 arquivo | ✅ Granular |
| T3: CollectS3KeysForChat ext | 1 arquivo | ✅ Granular |
| T4: CreateUserMessageAndJob ext | 1 arquivo | ✅ Granular |
| T5: DispatchPayload field | 1 arquivo | ✅ Granular |
| T6: validateAndUploadAttachments helper | 1 arquivo | ✅ Granular |
| T7: Handler multipart + service.PostMessage param | 2 arquivos acoplados (handler + service do mesmo método) | ✅ Aceitável (vertical slice do endpoint) |
| T8: refreshContentImageURLs ext | 1 arquivo | ✅ Granular |
| T9: chatContentJSON ext | 1 arquivo | ✅ Granular |
| T10: state.py fields | 1 arquivo | ✅ Granular |
| T11: s3_image_utils + refactor describe_references | 2 arquivos (extract + caller) | ✅ Aceitável (refactor mecânico) |
| T12: describe_user_attachments node + prompt | 2 arquivos (prompt = dependência direta) | ✅ Aceitável |
| T13: render_to_jpeg allowlist | 1 arquivo | ✅ Granular |
| T14: prompt generate_slides | 1 arquivo | ✅ Granular |
| T15: prompt edit_slides | 1 arquivo | ✅ Granular |
| T16: attachment_block helper | 1 arquivo | ✅ Granular |
| T17: main.py DispatchPayload + initial_state | 1 arquivo | ✅ Granular |
| T18: graph.py rewire | 1 arquivo | ✅ Granular |
| T19: integrar block em 3 nós | 3 arquivos (mesma mudança mecânica) | ✅ Aceitável (mesma operação repetida; extrair para 1 task vs 3 commits idênticos) |
| T20: api/chats.ts types + postChatMessage | 1 arquivo | ✅ Granular |
| T21: ComposerBar | 1 arquivo | ✅ Granular |
| T22: MessageBubbleUser | 1 arquivo | ✅ Granular |
| T23: Chat.tsx + ChatThread acoplados | 2 arquivos (otimista + render) | ✅ Aceitável |
| T24: JobStatusIndicator (P3) | 1 arquivo + caller | ✅ Aceitável |
| T25: integration test multipart | 1 arquivo | ✅ Granular |
| T26: integration test cleanup | 1 arquivo (mesmo de T25 ou separado) | ✅ Granular |
