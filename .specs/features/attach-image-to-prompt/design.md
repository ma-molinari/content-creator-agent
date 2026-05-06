# Anexar Imagem ao Prompt — Design

**Spec**: `.specs/features/attach-image-to-prompt/spec.md`
**Context**: `.specs/features/attach-image-to-prompt/context.md`
**Status**: Draft

---

## Architecture Overview

A feature atravessa as três camadas (Web → API Go → Worker Python) e o S3, mantendo o contrato assíncrono atual de jobs (`POST /chats/:id/messages → 202 + jobId` + callback). Único endpoint HTTP que muda de **content-type**: `POST /chats/:id/messages` passa a aceitar **`multipart/form-data`** (mantendo retrocompatibilidade com `application/json` quando não há anexos). Toda a persistência S3 dos anexos do usuário acontece **antes** da criação de `ChatContent` e `Job` para garantir que falhas de upload nunca deixem mensagem órfã.

```
┌───────────────┐  multipart  ┌──────────────────────────┐  HTTP   ┌─────────────────────┐
│ ComposerBar   │ ───────────►│  POST /chats/:id/messages │ ───────►│  Worker /jobs       │
│ + AttachIcon  │   text +    │  - validate                │ payload │  (FastAPI)          │
│ + thumbnails  │   files     │  - sniff mime              │   +     │  + new node         │
└──────┬────────┘             │  - S3 upload (per file)    │ s3 keys │  describe_user_     │
       │                      │  - persist attachments     │         │   attachments        │
       │                      │  - create ChatContent+Job  │         │  + generate/edit     │
       │                      │  - dispatch worker         │         │     consumes         │
       │                      └──────────┬─────────────────┘         └─────────┬───────────┘
       │                                 │                                     │
       │ thumbnails                      │  cascade ON DELETE                  │  HTML uses
       │ (signed URL)                    │                                     │  S3 image URLs
       │                                 ▼                                     ▼
       │                      ┌──────────────────────────┐         ┌─────────────────────┐
       └─────────────────────►│  PostgreSQL              │         │  Playwright render  │
                              │  + chat_content_         │         │  (allowlist + S3)   │
                              │     attachment table     │         └──────────┬──────────┘
                              │  + ChatContent           │                    │
                              └──────────┬───────────────┘                    │
                                         │                                    │
                                         │  CollectS3KeysForChat              │
                                         │  (incluí attachments)              │
                                         ▼                                    │
                              ┌──────────────────────────┐                    │
                              │  AWS S3                  │◄───────────────────┘
                              │  users/<uid>/chat-       │   POST /internal/jobs/:id/complete
                              │  attachments/<uuid>.<ext>│   (slides + assistant_text)
                              │  slides/<job>/...        │
                              └──────────────────────────┘
```

**Sequência de uma mensagem com 2 anexos:**
1. Web envia `multipart` (texto + 2 imagens).
2. API valida + sniffa mime real + faz upload S3 (paralelo) → falha em qualquer um → aborta com 4xx/5xx **sem** persistir nada.
3. API persiste `ChatContent (user)` + 2 `chat_content_attachment` + `Job (processing)` em **uma transação**.
4. API dispara worker incluindo `user_attachment_s3_keys: [...]` no `DispatchPayload`.
5. Worker grafo passa por `describe_user_attachments` (novo nó) entre `describe_references` e `detect_intent`, que decide se há instrução explícita e popula `user_attachment_intent` no `AgentState`.
6. `generate_slides` (ou `edit_slides`) recebe instrução clara no prompt: imagem(s) disponíveis em URL `<...>` + intenção (capa do slide 1 / específica).
7. HTML gerado referencia as imagens via URL S3 presignada; Playwright pode buscá-las graças ao **allowlist estendido** (`*.amazonaws.com` + bucket).
8. Pipeline segue inalterado a partir de `parse_validate`.

---

## Code Reuse Analysis

### Existing Components to Leverage

| Component | Location | How to Use |
| --- | --- | --- |
| `profile.UploadReferenceImage` (validação mime + upload S3) | `apps/api/internal/profile/service.go` | Replicar lógica de **mime sniff + ext + key UUID** num novo helper compartilhado (ou em `chat/service.go`); não chamar diretamente para manter SRP |
| `extForImageType` / `allowedImageContentType` | `apps/api/internal/profile/service.go` | Promover a função pública compartilhada (mover para `internal/storage` ou `internal/imageutil`) e reutilizar; ou copiar conscientemente se promoção for cara |
| `Repository.CollectS3KeysForChat` | `apps/api/internal/chat/repository.go` | Estender para incluir `chat_content_attachment.s3_key` no UNION → garantia automática de cleanup em delete + eviction |
| `Service.DeleteChat` / `CreateChat` (eviction) | `apps/api/internal/chat/service.go` | Não precisa mudar — usa o `CollectS3KeysForChat` já estendido |
| `Service.refreshContentImageURLs` | `apps/api/internal/chat/service.go` | Estender para também gerar signed URLs para `Attachments` em cada `ChatContent` user |
| `chatContentJSON` + `chatToJSON` | `apps/api/internal/chat/handler.go` | Adicionar campo `attachments` opcional |
| `DispatchPayload` | `apps/api/internal/jobs/worker_client.go` | Adicionar campo `UserAttachmentS3Keys []string` no padrão de `ReferenceS3Keys` |
| `describe_references` (vision via S3) | `apps/worker/app/nodes/describe_references.py` | **Padrão de código** para o novo `describe_user_attachments` (S3 fetch paralelo + vision LLM + erros graceful) |
| `_fetch_bytes_limited` / `_guess_mime` / `_S3GetObjectClient` | `apps/worker/app/nodes/describe_references.py` | Promover a `app/s3_image_utils.py` (ou similar) e reusar nos dois nós |
| `_allow_slide_route` (Playwright allowlist) | `apps/worker/app/nodes/render_to_jpeg.py` | **Estender** allowlist para permitir URL S3 presignada (host configurável: `*.amazonaws.com` ou `bucket.s3.region.amazonaws.com`) |
| `MessageBubbleUser` | `apps/web/src/components/chat/MessageBubbleUser.tsx` | Estender prop para `attachments?: AttachmentView[]` + grid de thumbnails + integração com `SlideViewer`-like lightbox |
| `ComposerBar` | `apps/web/src/components/composer/ComposerBar.tsx` | Adicionar botão de clipe + `<input type="file">` oculto + state de anexos com previews |
| Padrão axios + `responseType: 'blob'` em `api/chats.ts` | `apps/web/src/api/chats.ts` | Usar `FormData` no `postChatMessage` (atualmente JSON) |
| Toast (`lib/toast.ts`) | `apps/web/src/lib/toast.ts` | Mensagens de validação client-side |

### Integration Points

| System | Integration Method |
| --- | --- |
| **PostgreSQL** | Nova migration `013_chat_content_attachment.{up,down}.sql` + novo struct GORM `ChatContentAttachment` (FK para `chat_content`, `ON DELETE CASCADE`) |
| **S3** | Novo prefixo `users/<userID>/chat-attachments/<uuid>.<ext>` (alinhado com `users/<userID>/design-refs/...` de profile) |
| **Worker dispatch** | Novo campo `user_attachment_s3_keys` no `DispatchPayload` (mesmo padrão de `reference_s3_keys`) |
| **Worker callback** | **Inalterado** — anexos do usuário não viram artifacts (são input, não output) |
| **Vision/LLM** | Reutiliza `ChatOpenAI` com modelo de visão (`reference_vision_model` já configurado); novo nó retorna texto descritivo + intenção (estruturada via JSON) injetada no contexto de `optimize_prompt`/`generate_slides`/`edit_slides` |
| **Playwright render** | Estender allowlist em `_allow_slide_route` para o host S3 do bucket configurado (`Settings.aws_s3_bucket` + região) |

---

## Components

### Backend (Go API)

#### `ChatContentAttachment` (GORM model + table)

- **Purpose**: Persiste metadata do anexo do usuário (chave S3, mime, tamanho, ordem).
- **Location**: `apps/api/internal/db/models.go`, migration em `apps/api/internal/db/migrations/013_chat_content_attachment.{up,down}.sql`
- **Schema**:
  ```sql
  CREATE TABLE chat_content_attachment (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_content_id UUID NOT NULL REFERENCES chat_content(id) ON DELETE CASCADE,
    s3_key          VARCHAR(512) NOT NULL,
    mime_type       VARCHAR(64)  NOT NULL,
    size_bytes      BIGINT       NOT NULL,
    sort_order      INT          NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
  );
  CREATE INDEX idx_chat_content_attachment_content_id ON chat_content_attachment(chat_content_id);
  ```
- **Reuses**: Padrão `user_profile_references` (FK + s3_key + sort_order), padrão `ChatContentImage` (FK CASCADE).

#### `chat.AttachmentRepository` (ou métodos no Repository existente)

- **Purpose**: CRUD para `chat_content_attachment`; coleta de keys para cleanup.
- **Location**: `apps/api/internal/chat/repository.go` (métodos novos no Repository existente — mantém SRP do "chat aggregate root")
- **Interfaces**:
  - `CreateAttachmentsForContent(ctx, contentID uuid.UUID, items []AttachmentInput) error`
  - `ListAttachmentsForContent(ctx, contentID uuid.UUID) ([]db.ChatContentAttachment, error)`
  - `CollectS3KeysForChat(...)` — **estender** UNION para incluir `chat_content_attachment.s3_key`
- **Reuses**: Padrão GORM em `repository.go`; transação já usada em `CreateUserMessageAndJob`.

#### `chat.PostMessage` (extensão)

- **Purpose**: Aceitar lista de bytes+metadata de anexos; uploadar S3 antes da persistência; ligar a `ChatContent`.
- **Location**: `apps/api/internal/chat/post_message.go` + `service.go`
- **Mudanças**:
  1. Nova estrutura `AttachmentInput { Data []byte; MimeType string; SizeBytes int64; SortOrder int }`.
  2. Validação por arquivo: `len(Data) <= 5MB` + `http.DetectContentType` (mime real) + lista permitida (`image/jpeg|png|webp`).
  3. Validação agregada: `len(attachments) <= 4`.
  4. Upload S3 paralelo (errgroup) → key `users/<userID>/chat-attachments/<uuid>.<ext>`.
  5. Em qualquer falha do upload: best-effort delete do que já subiu + retornar erro **antes** de criar `ChatContent` ou `Job` (sem mensagem órfã).
  6. Persistir `ChatContent` + `chat_content_attachment` + `Job` em **uma transação** (estender `CreateUserMessageAndJob`).
  7. Adicionar `UserAttachmentS3Keys: keys` no `DispatchPayload`.
- **Reuses**: `SanitizeUserInput`, `loadAuditBrandTexts`, `latestAssistantHTMLKeys`, `ChatHasAssistantWithSlideArtifacts`.
- **Sentinel errors novos**: `ErrAttachmentTooLarge`, `ErrAttachmentInvalidType`, `ErrTooManyAttachments`, `ErrAttachmentUploadFailed`.

#### `chat.Handler.PostMessage` (extensão multipart)

- **Purpose**: Aceitar `multipart/form-data` mantendo compat JSON.
- **Location**: `apps/api/internal/chat/handler.go`
- **Lógica**:
  - Detectar `Content-Type: multipart/form-data` → ler `c.FormValue("content")` + `c.MultipartForm()` files com chave `attachments`.
  - Caso contrário → manter binding JSON atual (retrocompat).
  - Limite total de payload imposto via `middleware.BodyLimit(...)` específico para essa rota (ex.: `4 × 5MB + 32KB margem ≈ 22MB`); ou já configurado globalmente com folga.
  - Mapear novos sentinels para HTTP: 413 (`ErrAttachmentTooLarge`), 400 (`ErrAttachmentInvalidType`, `ErrTooManyAttachments`), 502 (`ErrAttachmentUploadFailed` por falha S3).
- **Reuses**: Padrão multipart de `profile.PostReference`; `mapChatErr`.

#### `chat.refreshContentImageURLs` (extensão)

- **Purpose**: Gerar signed URLs frescas para anexos do usuário também.
- **Location**: `apps/api/internal/chat/service.go`
- **Mudança**: iterar também `Contents[i].Attachments[j]` e popular `URL` (campo derivado, não persistido).
- **Reuses**: `store.GetSignedURL` já chamado para imagens.

#### `chatContentJSON` (extensão)

- **Purpose**: Expor anexos no payload JSON de `GET /chats/:id`.
- **Location**: `apps/api/internal/chat/handler.go`
- **Schema novo**:
  ```json
  {
    "id": "...",
    "role": "user",
    "content": "texto",
    "attachments": [
      { "id": "uuid", "url": "https://signed...", "mimeType": "image/jpeg", "sortOrder": 0 }
    ]
  }
  ```

### Backend (Worker Python)

#### `state.py` (extensão)

- **Purpose**: Carregar chaves de anexos do payload + estado da intenção detectada.
- **Location**: `apps/worker/app/state.py`
- **Novos campos `AgentState`** (todos `NotRequired`):
  - `user_attachment_s3_keys: NotRequired[list[str]]`
  - `user_attachment_descriptions: NotRequired[list[str]]` — descrição vision por anexo (índice alinhado com keys)
  - `user_attachment_intent: NotRequired[str]` — `"explicit"` (instrução clara no prompt) ou `"cover_default"` (sem instrução → capa)
  - `user_attachment_signed_urls: NotRequired[list[str]]` — URLs presignadas para uso no HTML dos slides

#### `describe_user_attachments` (novo nó)

- **Purpose**: Para cada imagem anexada, gerar URL presignada + descrição visual curta + classificar intenção do usuário (explícita vs default-capa).
- **Location**: `apps/worker/app/nodes/describe_user_attachments.py` + prompt `apps/worker/prompts/describe_user_attachments.md`
- **Interfaces**:
  - `async def describe_user_attachments(state: AgentState) -> dict`
- **Lógica**:
  1. Se `user_attachment_s3_keys` vazio → retorna `{}` (no-op).
  2. Para cada key: gerar URL presignada (1h) usando boto3 (mesma config do `describe_references`).
  3. Em paralelo, fetch dos bytes (limitado por `reference_image_max_bytes` reutilizado) e enviar ao vision LLM com prompt curto pedindo: tipo de imagem (foto, ilustração, screenshot, ícone), elementos principais, paleta dominante.
  4. Classificar intenção via heurística regex em `raw_message` (procurar padrões: "use", "coloque", "ponha", "no slide N", "como capa", "como fundo") → se match → `"explicit"`, senão `"cover_default"`.
  5. Retornar `{user_attachment_descriptions, user_attachment_intent, user_attachment_signed_urls}`.
  6. Falhas de S3/vision → log + degradação segura (descrição vazia, intenção `"cover_default"`, urls populadas se possível).
- **Reuses**: `_fetch_bytes_limited`, `_guess_mime`, padrão de `ChatOpenAI` + `HumanMessage` com blocks de imagem do `describe_references`. Nova helper `app/s3_image_utils.py` para promover essas funções.

#### `graph.py` (rewire)

- **Purpose**: Inserir `describe_user_attachments` entre `describe_references` e `detect_intent`.
- **Location**: `apps/worker/app/graph.py`
- **Mudança**:
  ```
  describe_references → describe_user_attachments → detect_intent → ...
  ```
- **Reuses**: `add_node` + `add_edge` existentes.

#### `optimize_prompt`, `generate_slides`, `edit_slides` (extensão de prompt context)

- **Purpose**: Quando há anexos, injetar bloco descritivo no contexto user-side da chamada LLM:
  ```
  <anexos_do_usuario count="2" intent="cover_default">
    <imagem n="1" url="https://signed-url-1" mime="image/jpeg">
      Foto retangular, plano fechado de teclado mecânico iluminado.
      Paleta: roxo escuro + cyan neon. Estilo: cinematográfico.
    </imagem>
    <imagem n="2" url="https://signed-url-2" mime="image/png">
      Logotipo "MoliStack" — texto em fonte sans-serif geométrica.
    </imagem>
  </anexos_do_usuario>

  ORIENTAÇÃO DE USO:
  - intent=cover_default → use IMAGEM 1 como visual dominante (hero/fundo) do slide 1 (capa);
    imagens adicionais são apoio em slides intermediários ou ignoradas se não couberem.
  - intent=explicit → siga estritamente a instrução do usuário em <raw_message>.
  - SEMPRE referencie a imagem por URL completa em `src=` ou `background-image: url(...)`.
  - NUNCA omita a tag <img> ou background quando a intenção determinar uso obrigatório.
  ```
- **Location**: `apps/worker/app/nodes/optimize_prompt.py`, `generate_slides.py`, `edit_slides.py` + prompts em `apps/worker/prompts/`
- **Reuses**: Padrão de montagem de `user_content` já existente nos nós.

#### `render_to_jpeg._allow_slide_route` (extensão allowlist)

- **Purpose**: Permitir URLs S3 presignadas durante a renderização Playwright.
- **Location**: `apps/worker/app/nodes/render_to_jpeg.py`
- **Mudança**:
  ```python
  from app.config import get_settings
  settings = get_settings()
  bucket = settings.aws_s3_bucket
  region = settings.aws_region
  allowed_s3_hosts = {
      f"{bucket}.s3.{region}.amazonaws.com",
      f"{bucket}.s3.amazonaws.com",
      f"s3.{region}.amazonaws.com",
  }
  # dentro de _allow_slide_route: parse url host → if host in allowed_s3_hosts: continue_
  ```
- **Reuses**: `get_settings`. Mantém a postura defensiva (deny-by-default exceto allowlist).

### Frontend (Web)

#### `ComposerBar` (extensão)

- **Purpose**: Botão de clipe + state de anexos + thumbnails inline + envio multipart.
- **Location**: `apps/web/src/components/composer/ComposerBar.tsx`
- **Mudanças**:
  - Novo state: `attachments: { id: string; file: File; previewUrl: string }[]`
  - Botão (`IconPaperclip`) à esquerda do textarea → abre `<input type="file" accept="image/jpeg,image/png,image/webp" multiple hidden>`.
  - Validação client: aceita só os primeiros que cabem dentro do limite (4 total, 5MB cada, mime válido); para os rejeitados → toast com motivo.
  - Thumbnails em grid horizontal acima do textarea, cada um com botão **×** (revoga `URL.createObjectURL`).
  - `onSend` muda assinatura para `(text: string, files: File[]) => Promise<void>`.
  - Em sucesso: limpar thumbnails + revogar URLs. Em erro: preservar.
- **Reuses**: `useRef` + `URL.createObjectURL` (padrão browser); `toast` para erros.

#### `api/chats.ts` (extensão `postChatMessage`)

- **Purpose**: Enviar `multipart/form-data` quando há anexos; manter JSON quando não há.
- **Location**: `apps/web/src/api/chats.ts`
- **Interface**:
  ```ts
  postChatMessage(chatId: string, content: string, attachments?: File[]): Promise<{ jobId: string }>
  ```
- **Lógica**:
  - Sem `attachments` → `POST` com `application/json` (preserva código existente).
  - Com `attachments` → `FormData`: `content` (string) + `attachments` (cada arquivo) → `POST` com `multipart/form-data` (axios infere automaticamente).
- **Reuses**: `api` (axios client com interceptor 401/refresh).

#### `MessageBubbleUser` (extensão)

- **Purpose**: Renderizar thumbnails dos anexos dentro da bolha.
- **Location**: `apps/web/src/components/chat/MessageBubbleUser.tsx`
- **Mudanças**:
  - Aceitar prop `attachments?: { id: string; url: string; mimeType: string }[]`.
  - Se `attachments?.length > 0` → grid horizontal de thumbnails acima do texto.
  - Click no thumbnail → abre lightbox (componente reutilizável; pode extrair lógica do `SlideViewer` em `Lightbox` standalone se ainda não existir, ou inline).
  - Erro de carregamento (`onError` da img) → placeholder com ícone "imagem indisponível".
- **Reuses**: Padrão visual de `SlideViewer`; tokens CSS do projeto.

#### `Chat.tsx` / `ChatThread` (passar attachments adiante)

- **Purpose**: Repassar `attachments` da `ChatContent` (vinda da API) ao `MessageBubbleUser`.
- **Location**: `apps/web/src/pages/Chat.tsx` + `apps/web/src/components/chat/ChatThread.tsx`
- **Mudança**: Tipos em `api/chats.ts` ganham `attachments?: ChatContentAttachment[]`; thread renderiza condicionalmente. Bolha otimista (pendente) também precisa receber as `Files` do envio para preview imediato (criar object URLs locais até o GET trazer do servidor).

#### `JobStatusIndicator` (P3 — opcional)

- **Purpose**: Mostrar label adicional quando o job atual tem anexos.
- **Location**: `apps/web/src/components/chat/JobStatusIndicator.tsx`
- **Mudança mínima**: nova prop `hasUserAttachments?: boolean` → quando true e status `processing`, label vira "Aplicando imagens anexadas…".
- **Pode ser deferido se Design phase considerar não trivial.**

---

## Data Models

### `ChatContentAttachment` (Go)

```go
// apps/api/internal/db/models.go
type ChatContentAttachment struct {
    ID            uuid.UUID   `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
    ChatContentID uuid.UUID   `gorm:"type:uuid;not null;index"`
    ChatContent   ChatContent `gorm:"constraint:OnDelete:CASCADE"`
    S3Key         string      `gorm:"column:s3_key;size:512;not null"`
    MimeType      string      `gorm:"column:mime_type;size:64;not null"`
    SizeBytes     int64       `gorm:"column:size_bytes;not null"`
    SortOrder     int         `gorm:"column:sort_order;not null;default:0"`
    CreatedAt     time.Time
    // Não persistido — populado por refreshContentImageURLs
    URL string `gorm:"-"`
}

func (ChatContentAttachment) TableName() string { return "chat_content_attachment" }

// Adicionar em ChatContent:
type ChatContent struct {
    // ...existentes...
    Attachments []ChatContentAttachment `gorm:"foreignKey:ChatContentID"`
}
```

**Relationships**:
- `ChatContentAttachment.ChatContentID → ChatContent.ID` com `ON DELETE CASCADE` (DB e GORM).
- `ChatContent.Attachments` carregado via Preload no mesmo lugar onde `Images` já é carregado em `GetByIDWithContents`.

### Migration `013_chat_content_attachment`

```sql
-- 013_chat_content_attachment.up.sql
CREATE TABLE chat_content_attachment (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_content_id UUID NOT NULL REFERENCES chat_content(id) ON DELETE CASCADE,
    s3_key          VARCHAR(512) NOT NULL,
    mime_type       VARCHAR(64)  NOT NULL,
    size_bytes      BIGINT       NOT NULL,
    sort_order      INT          NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_chat_content_attachment_content_id ON chat_content_attachment(chat_content_id);

-- 013_chat_content_attachment.down.sql
DROP INDEX IF EXISTS idx_chat_content_attachment_content_id;
DROP TABLE IF EXISTS chat_content_attachment;
```

### `DispatchPayload` (Go) — extensão

```go
type DispatchPayload struct {
    // ...existentes...
    UserAttachmentS3Keys []string `json:"user_attachment_s3_keys,omitempty"`
}
```

### Worker `DispatchPayload` (Pydantic) — extensão

```python
class DispatchPayload(BaseModel):
    # ...existentes...
    user_attachment_s3_keys: list[str] | None = None
```

### `chatContentJSON` (Go) — extensão

```go
type chatContentJSON struct {
    // ...existentes...
    Attachments []chatContentAttachJSON `json:"attachments,omitempty"`
}

type chatContentAttachJSON struct {
    ID        uuid.UUID `json:"id"`
    URL       string    `json:"url"`
    MimeType  string    `json:"mimeType"`
    SortOrder int       `json:"sortOrder"`
}
```

### TypeScript types — extensão `api/chats.ts`

```typescript
export type ChatContentAttachment = {
  id: string
  url: string
  mimeType: 'image/jpeg' | 'image/png' | 'image/webp'
  sortOrder: number
}

export type ChatContent = {
  // ...existentes...
  attachments?: ChatContentAttachment[]
}
```

---

## Error Handling Strategy

| Cenário | Camada | Tratamento | Resposta ao usuário |
| --- | --- | --- | --- |
| Mime inválido (sniff) | API | Retorna `ErrAttachmentInvalidType` | 400 `"formato inválido — apenas JPEG/PNG/WEBP"` |
| Tamanho > 5MB por arquivo | API | Retorna `ErrAttachmentTooLarge` | 413 `"imagem excede 5MB"` |
| Mais de 4 anexos | API | Retorna `ErrTooManyAttachments` | 400 `"máximo de 4 imagens por mensagem"` |
| Falha de upload S3 (parcial) | API | Best-effort delete dos uploads anteriores + retorna `ErrAttachmentUploadFailed` | 502 `"falha ao salvar anexos, tente novamente"`; **draft preservado no client** |
| Texto vazio + só imagens | API | Mantém regra atual `ErrEmptyPrompt` | 400 (mensagem existente) |
| Falha S3 fetch no worker | Worker | Log + degradar (descrição vazia, intent=cover_default, urls vazias) | Job continua; LLM gera sem ver a imagem (melhor que falhar tudo) |
| Falha vision LLM | Worker | Log + descrição vazia mas mantém URL para uso no HTML | Job continua; LLM ainda recebe URL para usar (img/background) |
| Playwright bloqueia URL S3 | Worker | Imagem aparece quebrada no JPEG; log de console captura | **Mitigação**: allowlist estendido (decisão técnica abaixo) garante que isso não acontece em ambiente bem configurado |
| URL signed expira durante render | Worker | URL gerada com 1h de validade — render acontece em segundos; risco quase nulo | N/A |
| Anexo órfão (criado mas mensagem não persistiu) | Não pode acontecer — upload é 1.º, persistência é 2.ª; em falha de persistência, fazer best-effort delete dos uploads | Worker nunca recebe; storage limpo |
| Delete de chat com anexos | API | `CollectS3KeysForChat` estendido inclui `chat_content_attachment.s3_key` | DB cascade + S3 delete em uma operação |
| Eviction (6º chat) | API | Mesmo path do delete via `CollectS3KeysForChat` | Sem leftovers |

---

## Technical Decisions

| Decisão | Escolha | Racional |
| --- | --- | --- |
| Upload no servidor (multipart) vs presigned PUT direto do client | **Multipart no servidor** | V1 simples, validação central, sem segredo extra; presigned PUT fica como deferred |
| Imagem no HTML do slide: base64 inline vs URL S3 presignada | **URL presignada** + extensão da allowlist Playwright | Mantém HTML leve (não inflar com bytes), facilita debug visual no browser, padrão consistente com Google Fonts já permitido |
| Tabela nova vs reusar `chat_content_image` | **Nova tabela `chat_content_attachment`** | `chat_content_image` tem `slide_number NOT NULL` e semântica de "JPEG do assistente"; misturar quebraria `CollectS3KeysForChat`, `GetLatestAssistantHTMLKeys` e queries de listagem |
| Onde validar mime: client, servidor, ou ambos | **Ambos** | Client previne UX ruim e reduz tráfego; servidor é a fonte de verdade (sniff dos primeiros bytes via `http.DetectContentType` — não confiar no header do client) |
| Detecção de intenção (explícita vs capa-default): no novo nó vs reaproveitar `detect_intent` existente | **No novo nó** `describe_user_attachments` via heurística regex + (opcionalmente) classificação LLM | `detect_intent` já tem responsabilidade de "edit vs new"; misturar quebra SRP. Heurística regex sobre `raw_message` é suficiente para V1 (palavras-chave: "use", "coloque", "no slide N", "como capa", "como fundo"); evolução futura → upgrade para classificação LLM |
| Posição do `describe_user_attachments` no grafo | Entre `describe_references` e `detect_intent` | Anexos do usuário são input visual independente; `detect_intent` precisa do `raw_message` mas não da descrição visual — porém `optimize_prompt`/`generate_slides`/`edit_slides` precisam, então rodar antes garante disponibilidade |
| Limite de 4 anexos | **4** | Decidido na fase de spec/context (agent's discretion); revisável após dados de uso |
| Mime types aceitos | **JPEG/PNG/WEBP** (sem GIF/HEIC) | Alinhado com `user_profile_references` no projeto e com o que renderiza bem no Playwright + Instagram |
| Tipo de transação para criar mensagem + anexos + job | **Estender `CreateUserMessageAndJob`** para também inserir os anexos | Mantém o atomic-write atual; rollback automático em qualquer falha |
| Fallback quando vision LLM falha | **Degradar (sem descrição) mas manter URL** | LLM ainda pode usar a imagem via URL no HTML mesmo sem ver o conteúdo; melhor que falhar o job inteiro |

---

## Research Notes

| Topic | Source | Finding |
| --- | --- | --- |
| Playwright route allowlist | Codebase: `apps/worker/app/nodes/render_to_jpeg.py` | `_allow_slide_route` já implementa `await route.continue_()` para Google Fonts e `data:`; estender com host check é trivial e seguro |
| Echo multipart parsing | Codebase: `apps/api/internal/profile/handler.go` (`PostReference`) | Padrão existente de `c.FormFile` e `c.MultipartForm()` já provado em produção; reutilizar |
| Mime sniff em Go | Codebase: `apps/api/internal/profile/service.go` (`http.DetectContentType`) | Stdlib resolve sem dep externa; `extForImageType` já mapeia para extensões |
| LangChain `HumanMessage` com bloco de imagem | Codebase: `apps/worker/app/nodes/describe_references.py` | Padrão de `{"type": "image_url", "image_url": {"url": "data:..."}}` já implementado e testado |
| S3 presigned URL no worker | A confirmar: `boto3.generate_presigned_url('get_object', ...)` é a API correta. **Codebase só usa `get_object` direto via boto3** atualmente; presigning é adição. | `boto3` doc confirma assinatura padrão; não precisa de Context7. Promover utilitário em `app/s3_image_utils.py`. |
| S3 host pattern para allowlist | Conhecimento geral validado pelo padrão atual de buckets | `<bucket>.s3.<region>.amazonaws.com` (virtual-hosted) ou `s3.<region>.amazonaws.com/<bucket>` (path-style); presigned URLs default ao virtual-hosted. |

---

## Risks & Mitigations

| Risco | Severidade | Mitigação |
| --- | --- | --- |
| LLM gera HTML que ignora a imagem mesmo com URL injetada | Média | Prompt explicitamente exige `<img src="..."/>` ou `background-image: url(...)`; `parse_validate` ou `design_validate` podem ganhar checagem opcional de presença da URL no HTML quando `intent=cover_default` |
| Playwright timeout buscando S3 | Baixa | Timeout do `set_content` já é 60s; presigned URL tem latência baixa em mesma região |
| Vision LLM caro / lento por anexo | Média | Limite de 4 anexos contém custo; descrição é curta (max_tokens ~400); fallback degrada se falhar |
| Tamanho total do payload multipart (4 × 5MB = 20MB) | Baixa | Configurar `BodyLimit` na rota PostMessage para `~22MB`; rejeitar maior antes de processar |
| Storage growth com chats deletados (regressão se cleanup falhar) | Alta | Spec exige inclusão em `CollectS3KeysForChat` — testar via integration test que delete remove anexos do bucket |
| Quebra de retrocompat para clients antigos (mobile/curl) | Baixa | Mantém JSON quando não há `multipart/form-data`; campo novo `attachments` é `omitempty` |
