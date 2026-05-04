# Iterative Slide Refinement — Design

**Spec**: `.specs/features/iterative-slide-refinement/spec.md`
**Context**: `.specs/features/iterative-slide-refinement/context.md`
**Status**: Draft

---

## Architecture Overview

A feature adiciona um **caminho de refinamento** paralelo ao pipeline LangGraph existente. Quando um chat já possui slides gerados, a API inclui as chaves S3 dos HTMLs fonte no payload de dispatch. O worker detecta a intenção do prompt (editar vs. criar novo) e roteia para `edit_slides` ou para o pipeline original, convergindo novamente em `parse_validate`.

```
POST /chats/:id/messages
  └─ PostMessage (chat/service)
       ├─ GetLatestAssistantHTMLKeys(chatID) → []string   ← NOVO
       └─ DispatchPayload { ..., existing_slide_html_s3_keys }  ← NOVO

Worker — LangGraph:

load_profile
  → prompt_security_validate
    ├─ rejected → finalize
    └─ ok → describe_references
               → detect_intent                        ← NÓ NOVO
                  ├─ is_refinement=True
                  │    → edit_slides                  ← NÓ NOVO
                  │         → parse_validate          (convergência)
                  └─ is_refinement=False
                       → optimize_prompt
                           → validate_brief
                               ├─ retry → optimize_prompt
                               ├─ fail  → finalize
                               └─ ok    → generate_slides
                                             → parse_validate  (convergência)

parse_validate
  ├─ retry → generate_slides   (fallback também para o caminho de edição)
  ├─ fail  → finalize
  └─ continue → design_validate
                  ├─ retry → generate_slides
                  ├─ fail  → finalize
                  └─ continue → render_to_jpeg
                                  → upload_assets     ← ESTENDIDO (+ HTML)
                                      → finalize      ← ESTENDIDO (+ htmlS3Key por artifact)

POST /internal/jobs/:id/complete
  └─ CompleteAssistantReply    ← ESTENDIDO (persiste html_s3_key em ChatContentImage)

NOVO endpoint:
GET /chats/:id/contents/:contentId/download → ZIP dos JPEGs daquela versão
```

---

## Code Reuse Analysis

### Existing Components to Leverage

| Component | Location | Como reutilizar |
|-----------|----------|-----------------|
| `validateSlideArtifactKey` | `apps/api/internal/jobs/slide_key.go` | Já valida `slides/{jobId}/` prefix + path traversal; funciona para `.html` sem alteração |
| `upload_assets` node | `apps/worker/app/nodes/upload_assets.py` | Extender: reutilizar `_upload_with_retry` para o upload do HTML |
| `generate_slides` node | `apps/worker/app/nodes/generate_slides.py` | `edit_slides` usa o mesmo padrão (LLM call → `raw_slide_output`) e mesma saída delimitada |
| `BuildChatZip` | `apps/api/internal/chat/service.go` | `BuildContentZip` reutiliza mesma lógica, filtrado por `ChatContentID` |
| `parse_validate` / `design_validate` | `apps/worker/app/nodes/` | Sem alteração — o caminho de edição converge aqui |
| `CompleteBody` / `CompleteAssistantReply` | `apps/api/internal/jobs/handler.go`, `complete.go` | Estender com `htmlS3Key` opcional sem quebrar contrato |

### Integration Points

| Sistema | Ponto de integração |
|---------|---------------------|
| `DispatchPayload` | Novo campo `ExistingSlideHTMLKeys []string` (omitempty — compatível com versões anteriores) |
| `CompleteBody.Artifacts` | Novo campo `HTMLs3Key *string` por artifact (pointer — retrocompatível) |
| `ChatContentImage` DB | Nova coluna `html_s3_key VARCHAR(512) NULL` (nullable — filas antigas ficam NULL) |
| LangGraph `AgentState` | 3 novos campos opcionais (`NotRequired`) — sem breaking change |

---

## Components

### 1. Migração DB — `012_add_html_s3_key`

- **Purpose**: adicionar `html_s3_key` nullable à tabela `chat_content_image`
- **Location**: `apps/api/internal/db/migrations/012_add_html_s3_key_to_chat_content_image.{up,down}.sql`
- **Schema**:
  ```sql
  -- up
  ALTER TABLE chat_content_image ADD COLUMN html_s3_key VARCHAR(512);
  -- down
  ALTER TABLE chat_content_image DROP COLUMN html_s3_key;
  ```
- **Reuses**: padrão de migration existente (numeração sequencial, par up/down)

---

### 2. `db.ChatContentImage` — novo campo

- **Purpose**: refletir a coluna `html_s3_key` no model GORM
- **Location**: `apps/api/internal/db/models.go`
- **Interface**:
  ```go
  type ChatContentImage struct {
      // ... campos existentes ...
      HtmlS3Key *string `gorm:"column:html_s3_key;size:512"` // nullable
  }
  ```

---

### 3. `chat/repository.go` — `GetLatestAssistantHTMLKeys`

- **Purpose**: retornar as chaves S3 HTML dos slides da versão mais recente do chat, para inclusão no dispatch
- **Location**: `apps/api/internal/chat/repository.go`
- **Interface**:
  ```go
  // GetLatestAssistantHTMLKeys returns html_s3_key values from the most recent
  // assistant ChatContent with slides for the given chat, ordered by slide_number.
  // Returns nil (no error) if no such content exists.
  func (r *Repository) GetLatestAssistantHTMLKeys(ctx context.Context, chatID uuid.UUID) ([]string, error)
  ```
- **Query**: JOIN `chat_content` (role=assistant) + `chat_content_image` (html_s3_key IS NOT NULL), ORDER BY `chat_content.created_at DESC`, LIMIT 1 para o content, depois todos os seus images ordenados por `slide_number`
- **Reuses**: padrão GORM existente do repositório

---

### 4. `chat/post_message.go` — inclusão de HTML keys no dispatch

- **Purpose**: buscar as chaves HTML da última versão e incluí-las no `DispatchPayload`
- **Location**: `apps/api/internal/chat/post_message.go` — método `PostMessage`
- **Change**: ao montar o `DispatchPayload` (após persistir mensagem do usuário e job), chamar `GetLatestAssistantHTMLKeys` / helper equivalente no service e popular `ExistingSlideHTMLKeys`; **não** enviar transcript nem resumo do cron ao worker — contexto iterativo para edição vem do HTML em S3 + `raw_message` atual
- **Error strategy**: se a query falhar → logar e continuar com `ExistingSlideHTMLKeys = nil` (degradação segura: trata como primeira geração)

---

### 5. `jobs/worker_client.go` — `DispatchPayload` estendido

- **Purpose**: transportar as chaves HTML para o worker
- **Location**: `apps/api/internal/jobs/worker_client.go`
- **Interface**:
  ```go
  type DispatchPayload struct {
      // ... campos existentes ...
      ExistingSlideHTMLKeys []string `json:"existing_slide_html_s3_keys,omitempty"`
  }
  ```

---

### 6. `jobs/handler.go` — `CompleteBody` estendido

- **Purpose**: aceitar `htmlS3Key` opcional por artifact no callback do worker
- **Location**: `apps/api/internal/jobs/handler.go`
- **Interface**:
  ```go
  type CompleteBody struct {
      AssistantText *string `json:"assistantText"`
      Artifacts     []struct {
          S3Key       string  `json:"s3Key"`
          SlideNumber int     `json:"slideNumber"`
          HTMLs3Key   *string `json:"htmlS3Key,omitempty"`
      } `json:"artifacts"`
      Error *string `json:"error"`
  }
  ```
- **Reuses**: estrutura existente — adição backward-compatible (campo opcional)

---

### 7. `jobs/complete.go` — persistência de `html_s3_key`

- **Purpose**: salvar `html_s3_key` no `ChatContentImage` quando presente no callback
- **Location**: `apps/api/internal/jobs/complete.go` — `CompleteAssistantReply`
- **Change**: no loop de criação de `ChatContentImage`, popular `HtmlS3Key` quando o artifact contém `HTMLs3Key` não-nil
- **Validation**: se `HTMLs3Key` não-nil, chamar `validateSlideArtifactKey(job.ID, *htmlKey)` — mesma função existente (a key segue o mesmo prefixo `slides/{jobID}/`)

---

### 8. `chat/service.go` — `BuildContentZip`

- **Purpose**: gerar ZIP dos JPEGs de uma versão específica (ChatContent)
- **Location**: `apps/api/internal/chat/service.go`
- **Interface**:
  ```go
  // BuildContentZip builds a ZIP of JPEG slides for a specific assistant ChatContent.
  // Returns ErrNotFound if the content doesn't exist, ErrForbidden if not owned,
  // ErrNoFiles if no images.
  func (s *Service) BuildContentZip(ctx context.Context, userID, chatID, contentID uuid.UUID) ([]byte, string, error)
  ```
- **Reuses**: lógica idêntica a `BuildChatZip`, filtrada por `ChatContentID`

---

### 9. `chat/handler.go` — `DownloadContentZip`

- **Purpose**: servir o ZIP de uma versão via HTTP
- **Location**: `apps/api/internal/chat/handler.go`
- **Route**: `GET /chats/:id/contents/:contentId/download`
- **Interface**:
  ```go
  func (h *Handler) DownloadContentZip(c echo.Context) error
  ```
- **Reuses**: padrão `DownloadZip` existente (headers Content-Type/Content-Disposition + c.Blob)

---

### 10. `apps/worker/app/state.py` — novos campos

- **Purpose**: estender `AgentState` com campos de refinamento
- **Location**: `apps/worker/app/state.py`
- **Novos campos**:
  ```python
  # Chaves S3 dos HTMLs da versão mais recente (enviados pelo API no dispatch)
  existing_slide_html_s3_keys: NotRequired[list[str]]
  # HTMLs carregados do S3 se is_refinement=True (conteúdo completo dos slides)
  existing_slide_html: NotRequired[list[SlideItem]]
  # True se detect_intent decidiu editar slides existentes
  is_refinement: NotRequired[bool]
  ```

---

### 11. `nodes/detect_intent.py` — novo nó

- **Purpose**: decidir se o prompt é refinamento de slides existentes ou nova criação, e carregar os HTMLs do S3 quando necessário
- **Location**: `apps/worker/app/nodes/detect_intent.py`
- **Lógica**:
  1. Se `existing_slide_html_s3_keys` está vazio → retorna `{"is_refinement": False, "existing_slide_html": []}` sem chamada LLM
  2. Chama LLM com `prompts/detect_intent.md` + `raw_message` → resposta JSON `{"intent": "edit" | "new"}`
  3. Se `"new"` → retorna `{"is_refinement": False, "existing_slide_html": []}`
  4. Se `"edit"` → busca HTMLs do S3 em paralelo (`asyncio.gather`) via `boto3` + `asyncio.to_thread`; retorna `{"is_refinement": True, "existing_slide_html": slides}`
- **Error handling**: falha no fetch S3 → logar + retornar `{"is_refinement": False, "existing_slide_html": [], "errors": [...]}` (degradação segura: trata como nova geração)
- **Prompt**: `prompts/detect_intent.md` — classificação binária, temperatura 0, modelo leve configurável (usa `OPENAI_CHAT_MODEL`)

---

### 12. `nodes/edit_slides.py` — novo nó

- **Purpose**: editar os HTMLs existentes conforme o prompt do usuário, produzindo saída no mesmo formato delimitado de `generate_slides`
- **Location**: `apps/worker/app/nodes/edit_slides.py`
- **Lógica**:
  1. Lê `existing_slide_html` (lista de `SlideItem`) e `raw_message`
  2. Constrói `user_content` com: bloco `<slides_existentes>` contendo os HTMLs + instrução do usuário
  3. Chama LLM com `prompts/edit_slides.md` como system prompt
  4. Retorna `{"raw_slide_output": raw}` — **idêntico ao contrato de `generate_slides`**
- **Output format**: o LLM é instruído a produzir blocos `###SLIDE_FILE: slide_NN.html` … `###END_SLIDE###` para **todos** os slides (editados ou inalterados) — `parse_validate` e `design_validate` funcionam sem alteração
- **Reuses**: padrão de `generate_slides` (LLM call, `langchain_message_text`, `compute_max_output_tokens`)

---

### 13. `nodes/upload_assets.py` — upload de HTML

- **Purpose**: além do JPEG, fazer upload do HTML fonte de cada slide
- **Location**: `apps/worker/app/nodes/upload_assets.py`
- **Change**:
  - Para cada slide renderizado, ler o HTML correspondente de `state["slides_html"]` pelo `filename` (alinhamento por índice já existente)
  - Upload HTML com key `slides/{job_id}/slide_{n}.html`, `ContentType="text/html"`
  - Adicionar `html_s3_key` ao `ArtifactRef` — campo opcional `html_s3_key: Optional[str]`
  - Falha no upload HTML → logar + `html_s3_key = None` (não bloqueia o JPEG)
- **Reuses**: `_upload_with_retry` existente, mesma lógica de backoff

---

### 14. `state.py` — `ArtifactRef` estendido

```python
class ArtifactRef(TypedDict):
    s3_key: str
    slide_number: int
    html_s3_key: NotRequired[Optional[str]]  # NOVO
```

---

### 15. `nodes/finalize.py` — inclui `htmlS3Key` no callback

- **Purpose**: passar a chave S3 do HTML fonte por artifact para a API
- **Location**: `apps/worker/app/nodes/finalize.py`
- **Change**: no `payload["artifacts"]`, incluir `"htmlS3Key": a.get("html_s3_key")` (None quando ausente — retrocompatível)

---

### 16. `graph.py` — roteamento

- **Purpose**: inserir `detect_intent` e `edit_slides` no grafo com roteamento condicional
- **Location**: `apps/worker/app/graph.py`
- **Changes**:
  ```python
  def route_after_detect_intent(state: AgentState) -> str:
      return "edit_slides" if state.get("is_refinement") else "optimize_prompt"

  builder.add_node("detect_intent", detect_intent)
  builder.add_node("edit_slides", edit_slides)

  # substituir: describe_references → optimize_prompt
  # por:
  builder.add_edge("describe_references", "detect_intent")
  builder.add_conditional_edges(
      "detect_intent",
      route_after_detect_intent,
      {"edit_slides": "edit_slides", "optimize_prompt": "optimize_prompt"},
  )
  builder.add_edge("edit_slides", "parse_validate")
  ```
- **Retry behavior**: se `parse_validate` ou `design_validate` precisar de retry após `edit_slides`, ambos já rotam para `generate_slides` — comportamento correto como fallback de geração limpa

---

### 17. `prompts/detect_intent.md` — classificação de intenção

- **Purpose**: system prompt para classificação binária edit/new
- **Location**: `apps/worker/prompts/detect_intent.md`
- **Estrutura**:
  - Persona: classificador de intenção para carrossel de slides
  - Tarefa: dado `raw_message`, responder **somente** `{"intent": "edit"}` ou `{"intent": "new"}`
  - Critérios: mensagens que mencionam alterar, ajustar, mudar, corrigir, refinar → "edit"; mensagens sobre novo tema, criar do zero, outro assunto → "new"; quando ambíguo → "edit" (conservador)
  - Temperatura: 0 (determinístico)

---

### 18. `prompts/edit_slides.md` — edição de HTML

- **Purpose**: system prompt para edição de slides existentes
- **Location**: `apps/worker/prompts/edit_slides.md`
- **Estrutura**:
  - Persona: editor de carrossel HTML/CSS para Instagram
  - Contexto: recebe slides existentes + instrução do usuário
  - Tarefa: aplicar apenas as mudanças pedidas, preservando layout/identidade visual dos demais
  - Restrições: mesmas do `generate_slides.md` (sem JS, sem URLs remotas, Google Fonts, viewport 1080×1350)
  - Formato: produzir **todos** os slides no formato `###SLIDE_FILE: slide_NN.html` … `###END_SLIDE###`

---

### 19. Frontend — `api/chats.ts`

- **Purpose**: expor função de download por versão
- **Location**: `apps/web/src/api/chats.ts`
- **Interface**:
  ```typescript
  export async function downloadContentZip(chatId: string, contentId: string): Promise<Blob>
  // GET /chats/:chatId/contents/:contentId/download
  ```

---

### 20. Frontend — `MessageAssistant`

- **Purpose**: label "Versão anterior" + botão de download por versão
- **Location**: `apps/web/src/components/chat/MessageAssistant.tsx`
- **Props novas**:
  ```typescript
  isLatestVersion: boolean  // true apenas para a última mensagem de assistente no thread
  ```
- **Changes**:
  - Se `!isLatestVersion`: exibir badge "Versão anterior" acima do `SlideViewer`
  - Botão de download por mensagem chama `downloadContentZip(chatId, content.id)` — independente do download ZIP geral do chat
- **Passagem da prop**: `ChatThread` (ou `Chat.tsx`) itera sobre mensagens, identifica a última de role=assistant, passa `isLatestVersion` correto

---

## Data Models

### `ChatContentImage` (atualizado)

```go
type ChatContentImage struct {
    ID            uuid.UUID
    ChatContentID uuid.UUID
    ChatContent   ChatContent
    S3Key         string      // JPEG key: slides/{jobId}/slide_N.jpeg
    URL           string      // presigned URL
    SlideNumber   int
    HtmlS3Key     *string     // HTML key: slides/{jobId}/slide_N.html (NULL = versão antiga)
    CreatedAt     time.Time
    UpdatedAt     time.Time
}
```

### `ArtifactRef` (worker, atualizado)

```python
class ArtifactRef(TypedDict):
    s3_key: str               # JPEG
    slide_number: int
    html_s3_key: NotRequired[Optional[str]]  # HTML, None se upload falhou
```

### `DispatchPayload` (atualizado)

```go
type DispatchPayload struct {
    JobID                 uuid.UUID `json:"job_id"`
    UserID                uuid.UUID `json:"user_id"`
    ChatID                uuid.UUID `json:"chat_id"`
    RawMessage            string    `json:"raw_message"`
    AuditText             string    `json:"audit_text"`
    BrandText             string    `json:"brand_text"`
    ReferenceS3Keys       []string  `json:"reference_s3_keys,omitempty"`
    ExistingSlideHTMLKeys []string  `json:"existing_slide_html_s3_keys,omitempty"` // refinamento
}
```

---

## Error Handling Strategy

| Cenário | Handling | Impacto no usuário |
|---------|----------|--------------------|
| `GetLatestAssistantHTMLKeys` falha | Log + continua sem HTML keys (trata como primeira geração) | Slide gerado do zero — sem erro visível |
| `detect_intent` LLM falha | Log + `is_refinement=False` + erro em `state["errors"]` | Geração do zero — sem erro visível |
| Fetch S3 do HTML falha no `detect_intent` | Log + `is_refinement=False` | Geração do zero — sem erro visível |
| Upload HTML falha no `upload_assets` | Log + `html_s3_key=None` no artifact; JPEG continua | Próximo refinamento trata como nova geração (sem HTML histórico) |
| `validateSlideArtifactKey` rejeita HTML key | `400 invalid s3Key` no callback | Job marcado failed — worker já trata isso |
| `parse_validate` ou `design_validate` retry após `edit_slides` | Roteia para `generate_slides` (fallback clean) | Slides regenerados do zero sem perda de dados |

---

## Technical Decisions

| Decisão | Escolha | Rationale |
|---------|---------|-----------|
| `html_s3_key` em `chat_content_image` vs. nova tabela | Coluna nullable na tabela existente | Um HTML por slide — mesmo granularidade do JPEG; evita JOIN adicional |
| `detect_intent` como nó separado vs. embutido em `edit_slides` | Nó separado | Separação de responsabilidade (classify vs. execute); detectar intenção com HTML ainda não carregado é mais eficiente |
| `edit_slides` produz mesmo formato que `generate_slides` | Sim — `###SLIDE_FILE:…###END_SLIDE###` | `parse_validate` e `design_validate` funcionam sem nenhuma mudança; retries para `generate_slides` como fallback |
| Retry após `edit_slides` → `generate_slides` (não `edit_slides`) | `generate_slides` | Se o HTML editado falhou validação repetidamente, regenerar limpo é mais robusto |
| Fetch de HTML no `detect_intent` (não em nó separado) | Mesmo nó | Evita nó extra; o fetch só acontece quando `is_refinement=True` |
| Temperatura 0 no `detect_intent` | Sim | Classificação determinística é mais importante que criatividade aqui |
| Transcript / resumo de chat no payload (`reprompt_context`) | Removido do contrato | “Memória” textual não vai mais ao worker; refinamento usa HTML histórico em S3 + pedido atual |
| Per-version download via `GET /chats/:id/contents/:contentId/download` | Novo endpoint | Segue padrão RESTful existente; não polui `GET /chats/:id/files` com parâmetros |

---

## Arquivos tocados

### API Go (6 + 1 novo handler)
| Arquivo | Tipo de mudança |
|---------|----------------|
| `apps/api/internal/db/models.go` | Adicionar `HtmlS3Key *string` em `ChatContentImage` |
| `apps/api/internal/db/migrations/012_*.{up,down}.sql` | Novo par de migrations |
| `apps/api/internal/jobs/worker_client.go` | Adicionar `ExistingSlideHTMLKeys` em `DispatchPayload` |
| `apps/api/internal/jobs/handler.go` | Adicionar `HTMLs3Key` em `CompleteBody.Artifacts` |
| `apps/api/internal/jobs/complete.go` | Persistir `HtmlS3Key` + validar |
| `apps/api/internal/chat/repository.go` | Novo método `GetLatestAssistantHTMLKeys` |
| `apps/api/internal/chat/post_message.go` | Chamar repo + incluir no payload |
| `apps/api/internal/chat/service.go` | Novo método `BuildContentZip` |
| `apps/api/internal/chat/handler.go` | Novo handler `DownloadContentZip` |
| `apps/api/cmd/server/main.go` | Registrar nova rota |

### Worker Python (6 novos / 4 editados)
| Arquivo | Tipo de mudança |
|---------|----------------|
| `apps/worker/app/state.py` | 3 novos campos em `AgentState` + `html_s3_key` em `ArtifactRef` |
| `apps/worker/app/nodes/detect_intent.py` | Novo nó |
| `apps/worker/app/nodes/edit_slides.py` | Novo nó |
| `apps/worker/app/nodes/upload_assets.py` | Upload HTML + `html_s3_key` em `ArtifactRef` |
| `apps/worker/app/nodes/finalize.py` | Incluir `htmlS3Key` no payload do callback |
| `apps/worker/app/graph.py` | Novos nós + roteamento condicional |
| `apps/worker/prompts/detect_intent.md` | Novo prompt |
| `apps/worker/prompts/edit_slides.md` | Novo prompt |

### Frontend React (2 editados)
| Arquivo | Tipo de mudança |
|---------|----------------|
| `apps/web/src/api/chats.ts` | Novo `downloadContentZip` |
| `apps/web/src/components/chat/MessageAssistant.tsx` | Prop `isLatestVersion` + badge + download por versão |
| `apps/web/src/components/chat/ChatThread.tsx` (ou similar) | Passar `isLatestVersion` para `MessageAssistant` |
