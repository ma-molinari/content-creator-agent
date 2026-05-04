# Iterative Slide Refinement — Tasks

**Design**: `.specs/features/iterative-slide-refinement/design.md`
**Status**: Aprovado

---

## Execution Plan

```
Phase 1 — DB Foundation (Sequential):
  T1 → T2

Phase 2 — Parallel (after T1/T2 para API; imediato para Worker):

  API track (after T2):            Worker track (independent):
    T3 [P]                           T7 [P]
    T4 [P]                             ├→ T8 [P]
    T5 [P]                             ├→ T9 [P]
    T6 [P]                             ├→ T10 [P]
                                       └→ T11 [P]

Phase 3 — Integration (Sequential):
  T3+T4 → T12
  T8+T9+T10+T11 → T13

Phase 4 — Frontend (after T6):
  T14 → T15
```

---

## Parallel Execution Map

```
Phase 1 (Sequential):
  T1 ──→ T2

Phase 2 (Parallel — dois tracks independentes):
  After T2:                     After nothing (worker independente):
    ├─ T3 [P]                     T7 ──→ T8 [P]
    ├─ T4 [P]                          ├─ T9 [P]
    ├─ T5 [P]                          ├─ T10 [P]
    └─ T6 [P]                          └─ T11 [P]

Phase 3 (Sequential):
  T3 + T4 ──→ T12
  T8 + T9 + T10 + T11 ──→ T13

Phase 4 (Sequential):
  T6 ──→ T14 ──→ T15

Critical path: T1 → T2 → T5 → (T12 paralela) → T13
Total tasks: 15 | Parallelizáveis: 10 | Phases: 4
```

---

## Task Breakdown

### T1: Migration SQL 012 — adicionar `html_s3_key`

**What**: Criar par de migrations SQL para adicionar coluna `html_s3_key VARCHAR(512) NULL` à tabela `chat_content_image`
**Where**:
- `apps/api/internal/db/migrations/012_add_html_s3_key_to_chat_content_image.up.sql`
- `apps/api/internal/db/migrations/012_add_html_s3_key_to_chat_content_image.down.sql`
**Depends on**: Nenhum
**Reuses**: Padrão de migration existente (`011_login_attempts.{up,down}.sql`)
**Requirement**: ISR-05

**Done when**:
- [ ] `up.sql`: `ALTER TABLE chat_content_image ADD COLUMN html_s3_key VARCHAR(512);`
- [ ] `down.sql`: `ALTER TABLE chat_content_image DROP COLUMN html_s3_key;`
- [ ] Arquivos nomeados com prefixo `012_` seguindo a sequência atual

**Verify**:
```bash
ls apps/api/internal/db/migrations/ | grep 012
```

**Commit**: `feat(db): add html_s3_key column to chat_content_image`

---

### T2: Model GORM — campo `HtmlS3Key` em `ChatContentImage`

**What**: Adicionar campo `HtmlS3Key *string` ao struct `ChatContentImage` em `models.go`
**Where**: `apps/api/internal/db/models.go`
**Depends on**: T1
**Reuses**: Padrão de campos nullable existentes (ex.: `Title *string` em `Chat`)
**Requirement**: ISR-05

**Done when**:
- [ ] `HtmlS3Key *string` adicionado com tag `gorm:"column:html_s3_key;size:512"`
- [ ] Campo é pointer (nullable) — registros antigos sem HTML ficam `nil`
- [ ] `go build ./...` sem erros

**Verify**:
```bash
cd apps/api && go build ./...
```

**Commit**: `feat(db): add HtmlS3Key field to ChatContentImage model`

---

### T3: Repository — `GetLatestAssistantHTMLKeys` [P]

**What**: Adicionar método `GetLatestAssistantHTMLKeys` no repositório de chat para buscar as chaves S3 HTML da versão mais recente
**Where**: `apps/api/internal/chat/repository.go`
**Depends on**: T2
**Reuses**: Padrão GORM de queries existentes no mesmo arquivo; joins `chat_content` + `chat_content_image`
**Requirement**: ISR-06

**Done when**:
- [ ] Assinatura: `GetLatestAssistantHTMLKeys(ctx context.Context, chatID uuid.UUID) ([]string, error)`
- [ ] Query: busca a `ChatContent` mais recente com `role=assistant` para o chat; retorna `html_s3_key` de seus `ChatContentImages` onde `html_s3_key IS NOT NULL`, ordenados por `slide_number`
- [ ] Retorna `nil, nil` (sem erro) se não existir conteúdo com HTML
- [ ] `go build ./...` sem erros

**Verify**:
```bash
cd apps/api && go build ./...
```

**Commit**: `feat(chat): add GetLatestAssistantHTMLKeys repository method`

---

### T4: `DispatchPayload` — campo `ExistingSlideHTMLKeys` [P]

**What**: Adicionar campo `ExistingSlideHTMLKeys []string` ao struct `DispatchPayload` em `worker_client.go`
**Where**: `apps/api/internal/jobs/worker_client.go`
**Depends on**: Nenhum
**Reuses**: Padrão `omitempty` já usado em `ReferenceS3Keys` e demais slices opcionais do payload
**Requirement**: ISR-06

**Done when**:
- [ ] Campo adicionado: `ExistingSlideHTMLKeys []string \`json:"existing_slide_html_s3_keys,omitempty"\``
- [ ] Campo não quebra nenhum `DispatchPayload{}` existente (slices nil não serializam com `omitempty`)
- [ ] `go build ./...` sem erros

**Verify**:
```bash
cd apps/api && go build ./...
```

**Commit**: `feat(jobs): add ExistingSlideHTMLKeys to DispatchPayload`

---

### T5: Callback — `HTMLs3Key` em `CompleteBody` + persistência [P]

**What**: Estender o callback do worker para aceitar e persistir a chave S3 do HTML por artifact
**Where**:
- `apps/api/internal/jobs/handler.go` — campo `HTMLs3Key *string` em `CompleteBody.Artifacts`
- `apps/api/internal/jobs/complete.go` — persistir `HtmlS3Key` + validar via `validateSlideArtifactKey`
**Depends on**: T2
**Reuses**: Struct `CompleteBody` existente; `validateSlideArtifactKey` existente (mesma lógica de prefixo)
**Requirement**: ISR-04, ISR-05

**Done when**:
- [ ] `CompleteBody.Artifacts` tem `HTMLs3Key *string \`json:"htmlS3Key,omitempty"\``
- [ ] `CompleteAssistantReply`: quando `HTMLs3Key != nil`, chama `validateSlideArtifactKey(job.ID, *htmlKey)` e popula `img.HtmlS3Key`
- [ ] Artifacts sem `htmlS3Key` continuam funcionando (retrocompatível)
- [ ] `go build ./...` + `go test ./internal/jobs/...` sem erros

**Verify**:
```bash
cd apps/api && go test ./internal/jobs/...
```

**Commit**: `feat(jobs): persist htmlS3Key per artifact in CompleteAssistantReply`

---

### T6: Download por versão — service + handler + rota [P]

**What**: Implementar endpoint `GET /chats/:id/contents/:contentId/download` que retorna ZIP dos JPEGs de uma versão específica
**Where**:
- `apps/api/internal/chat/service.go` — método `BuildContentZip`
- `apps/api/internal/chat/handler.go` — handler `DownloadContentZip`
- `apps/api/cmd/server/main.go` — registro da rota (grupo protegido por JWT)
**Depends on**: T2
**Reuses**: `BuildChatZip` (mesma lógica, filtrar por `ChatContentID`); `DownloadZip` handler (mesmos headers Content-Type/Disposition)
**Requirement**: ISR-08

**Done when**:
- [ ] `BuildContentZip(ctx, userID, chatID, contentID uuid.UUID) ([]byte, string, error)` implementado; retorna `ErrNotFound` se content não existe ou não pertence ao chat/usuário; `ErrNoFiles` se sem imagens
- [ ] Handler valida `chatID` e `contentID` como UUID; mapeia erros com `mapChatErr`
- [ ] Rota registrada em `main.go` no grupo JWT: `GET /chats/:id/contents/:contentId/download`
- [ ] `go build ./...` sem erros

**Verify**:
```bash
cd apps/api && go build ./...
```

**Commit**: `feat(chat): add per-version ZIP download endpoint`

---

### T7: `state.py` — novos campos [P]

**What**: Adicionar 3 novos campos a `AgentState` e campo `html_s3_key` a `ArtifactRef` em `state.py`
**Where**: `apps/worker/app/state.py`
**Depends on**: Nenhum
**Reuses**: Padrão `NotRequired` existente no mesmo arquivo
**Requirement**: ISR-01, ISR-04

**Done when**:
- [ ] `AgentState` tem: `existing_slide_html_s3_keys: NotRequired[list[str]]`, `existing_slide_html: NotRequired[list[SlideItem]]`, `is_refinement: NotRequired[bool]`
- [ ] `ArtifactRef` tem: `html_s3_key: NotRequired[Optional[str]]`
- [ ] `python -c "from app.state import AgentState, ArtifactRef"` sem erros

**Verify**:
```bash
cd apps/worker && python -c "from app.state import AgentState, ArtifactRef; print('ok')"
```

**Commit**: `feat(worker): add refinement fields to AgentState and ArtifactRef`

---

### T8: Prompt + nó `detect_intent` [P]

**What**: Criar prompt de classificação de intenção e o nó `detect_intent` que roteia entre refinamento e nova geração
**Where**:
- `apps/worker/prompts/detect_intent.md`
- `apps/worker/app/nodes/detect_intent.py`
**Depends on**: T7
**Reuses**: Padrão de nó LangGraph de `generate_slides.py` (async, `get_settings`, log `node=detect_intent job_id=...`); `read_prompt_md` de `config.py`; `copy_errors`
**Requirement**: ISR-01, ISR-02

**Done when**:
- [ ] `detect_intent.md`: system prompt de classificação binária que instrui o LLM a responder somente `{"intent": "edit"}` ou `{"intent": "new"}`; define critérios (refinamento → "edit", novo tema → "new", ambíguo → "edit" como default conservador)
- [ ] `detect_intent(state: AgentState) -> dict`: se `existing_slide_html_s3_keys` vazio → retorna `{"is_refinement": False, "existing_slide_html": []}` sem LLM; se não vazio → chama LLM com temperatura 0, parse JSON da resposta
- [ ] Quando `is_refinement=True`: faz fetch dos HTMLs do S3 via `asyncio.gather` + `asyncio.to_thread`; popula `existing_slide_html: list[SlideItem]`
- [ ] Falha no LLM ou no S3 → logar + `is_refinement=False` + erro em `state["errors"]` (degradação segura)
- [ ] `python -c "from app.nodes.detect_intent import detect_intent"` sem erros

**Verify**:
```bash
cd apps/worker && python -c "from app.nodes.detect_intent import detect_intent; print('ok')"
```

**Commit**: `feat(worker): add detect_intent node for refinement routing`

---

### T9: Prompt + nó `edit_slides` [P]

**What**: Criar prompt de edição e o nó `edit_slides` que edita os HTMLs existentes conforme o prompt do usuário
**Where**:
- `apps/worker/prompts/edit_slides.md`
- `apps/worker/app/nodes/edit_slides.py`
**Depends on**: T7
**Reuses**: Padrão de `generate_slides.py` (`ChatOpenAI`, `SystemMessage`/`HumanMessage`, `langchain_message_text`, `compute_max_output_tokens`, `read_prompt_md`); **saída idêntica**: `{"raw_slide_output": raw}`
**Requirement**: ISR-01, ISR-02

**Done when**:
- [ ] `edit_slides.md`: system prompt que instrui o LLM a editar os slides existentes preservando o layout e identidade visual; aplica somente as mudanças pedidas; produz **todos** os slides (editados + inalterados) no formato `###SLIDE_FILE: slide_NN.html` … `###END_SLIDE###`; mesmas restrições de design do `generate_slides.md` (sem JS, sem URLs remotas, Google Fonts, viewport 1080×1350)
- [ ] `edit_slides(state: AgentState) -> dict`: monta `user_content` com bloco `<slides_existentes>` contendo os HTMLs de `existing_slide_html` + instrução do usuário (`raw_message`)
- [ ] Retorna `{"raw_slide_output": raw}` — contrato idêntico a `generate_slides`
- [ ] `python -c "from app.nodes.edit_slides import edit_slides"` sem erros

**Verify**:
```bash
cd apps/worker && python -c "from app.nodes.edit_slides import edit_slides; print('ok')"
```

**Commit**: `feat(worker): add edit_slides node for iterative refinement`

---

### T10: `upload_assets.py` — upload HTML fonte [P]

**What**: Estender `upload_assets` para fazer upload do HTML fonte de cada slide em paralelo ao JPEG e popular `html_s3_key` no `ArtifactRef`
**Where**: `apps/worker/app/nodes/upload_assets.py`
**Depends on**: T7
**Reuses**: `_upload_with_retry` existente; `_slide_number_from_filename` existente; alinhamento entre `rendered_slides` e `slides_html` por índice
**Requirement**: ISR-04, ISR-07

**Done when**:
- [ ] Para cada slide renderizado, busca o HTML correspondente em `state["slides_html"]` pelo mesmo índice/filename
- [ ] Faz upload HTML com key `slides/{job_id}/slide_{n}.html` e `ContentType="text/html"`
- [ ] `ArtifactRef` retornado inclui `html_s3_key` quando upload HTML ok; `None` quando falha (falha no HTML não bloqueia o JPEG)
- [ ] Falha no upload HTML: logar com `node=upload_assets job_id=... slide=... err=...` e continuar
- [ ] `python -c "from app.nodes.upload_assets import upload_assets"` sem erros

**Verify**:
```bash
cd apps/worker && python -c "from app.nodes.upload_assets import upload_assets; print('ok')"
```

**Commit**: `feat(worker): upload HTML source alongside JPEG in upload_assets`

---

### T11: `finalize.py` — incluir `htmlS3Key` no callback [P]

**What**: Estender o payload do callback para incluir `htmlS3Key` por artifact quando disponível
**Where**: `apps/worker/app/nodes/finalize.py`
**Depends on**: T7
**Reuses**: Loop de construção de `payload["artifacts"]` existente
**Requirement**: ISR-04

**Done when**:
- [ ] `payload["artifacts"]` inclui `"htmlS3Key": a.get("html_s3_key")` por artifact
- [ ] Quando `html_s3_key` é `None`, o campo é enviado como `null` no JSON (API aceita por ser pointer `*string`)
- [ ] `python -c "from app.nodes.finalize import finalize"` sem erros

**Verify**:
```bash
cd apps/worker && python -c "from app.nodes.finalize import finalize; print('ok')"
```

**Commit**: `feat(worker): include htmlS3Key in finalize callback payload`

---

### T12: `post_message.go` — incluir HTML keys no dispatch

**What**: Atualizar `PostMessage` para buscar as chaves HTML da última versão e incluí-las no `DispatchPayload`
**Where**: `apps/api/internal/chat/post_message.go`
**Depends on**: T3, T4
**Reuses**: Padrão de chamada ao repositório no mesmo método (`loadAuditBrandTexts`, listagem de refs); estratégia de degradação segura (`profileSvc != nil`)
**Requirement**: ISR-06

**Done when**:
- [ ] Ao montar o dispatch (após `CreateUserMessageAndJob`), chama `GetLatestAssistantHTMLKeys` / helper no service equivalente a `s.repo.GetLatestAssistantHTMLKeys(ctx, chatID)`
- [ ] Em caso de erro: logar com `[chat] latest html keys chat_id=... err=...` e continuar com `htmlKeys = nil` (não interrompe o job)
- [ ] `ExistingSlideHTMLKeys: htmlKeys` populado no `DispatchPayload`
- [ ] `go build ./...` + `go test ./internal/chat/...` sem erros

**Verify**:
```bash
cd apps/api && go test ./internal/chat/...
```

**Commit**: `feat(chat): include existing slide HTML keys in worker dispatch payload`

---

### T13: `graph.py` — novos nós + roteamento condicional

**What**: Inserir `detect_intent` e `edit_slides` no grafo LangGraph com roteamento condicional correto
**Where**: `apps/worker/app/graph.py`
**Depends on**: T8, T9, T10, T11
**Reuses**: Padrão de `add_conditional_edges` existente (ex.: `route_after_parse`, `route_after_design`); padrão `add_node` + `add_edge`
**Requirement**: ISR-01, ISR-02, ISR-03

**Done when**:
- [x] `detect_intent` e `edit_slides` adicionados como nós
- [x] Fluxo intencional: `describe_references → optimize_prompt → validate_brief → detect_intent` (não `describe_references → detect_intent` direto) — `edit_slides` e `design_validate` dependem de `optimized_brief` já validado
- [x] `route_after_detect_intent`: retorna `"edit"` se `state.get("is_refinement")` senão `"new"`; mapeamento `{"edit": "edit_slides", "new": "generate_slides"}`
- [x] `add_edge("edit_slides", "parse_validate")` — converge com `generate_slides → parse_validate`
- [x] `parse_validate` / `design_validate` mantêm `retry_edit` → `edit_slides` e `retry_new` → `generate_slides`
- [x] `python -c "from app.graph import graph; ..."` sem erros; nós incluem `detect_intent`, `edit_slides`

**Verify**:
```bash
cd apps/worker && python -c "from app.graph import graph; print('nodes:', sorted(graph.nodes))"
```

**Commit**: `feat(worker): wire detect_intent and edit_slides into LangGraph pipeline`

---

### T14: `api/chats.ts` — `downloadContentZip` [P]

**What**: Adicionar função `downloadContentZip` no módulo de API do frontend para download ZIP por versão
**Where**: `apps/web/src/api/chats.ts`
**Depends on**: T6
**Reuses**: Padrão de chamada `axios` existente no mesmo arquivo; padrão de `responseType: 'blob'` para downloads
**Requirement**: ISR-08

**Done when**:
- [ ] `downloadContentZip(chatId: string, contentId: string): Promise<Blob>` implementado
- [ ] Chama `GET /chats/:chatId/contents/:contentId/download` com `responseType: 'blob'`
- [ ] `npm run build` sem erros TypeScript

**Verify**:
```bash
cd apps/web && npm run build 2>&1 | grep -E "error|Error" | head -20
```

**Commit**: `feat(web/api): add downloadContentZip function for per-version download`

---

### T15: `MessageAssistant` + `ChatThread` — badge + download por versão

**What**: Adicionar badge "Versão anterior" e botão de download individual por mensagem de assistente no thread
**Where**:
- `apps/web/src/components/chat/MessageAssistant.tsx` — prop `isLatestVersion` + badge + botão de download
- `apps/web/src/components/chat/ChatThread.tsx` (ou equivalente) — identificar última mensagem de assistente e passar `isLatestVersion`
**Depends on**: T14
**Reuses**: `DownloadButton` existente como referência para estilo; padrão de props em `MessageAssistant`; `downloadContentZip` de T14
**Requirement**: ISR-08, ISR-09

**Done when**:
- [ ] `MessageAssistant` aceita `isLatestVersion: boolean`
- [ ] Quando `!isLatestVersion`: exibe badge/label visual "Versão anterior" acima do `SlideViewer`
- [ ] Cada `MessageAssistant` com imagens tem botão de download que chama `downloadContentZip(chatId, content.id)` e faz download do ZIP (trigger via `URL.createObjectURL`)
- [ ] `ChatThread` (ou `Chat.tsx`) identifica a última mensagem de assistente com imagens e passa `isLatestVersion={true}` somente para ela; todas as anteriores recebem `isLatestVersion={false}`
- [ ] `npm run build` sem erros TypeScript

**Verify**:
```bash
cd apps/web && npm run build 2>&1 | grep -E "error|Error" | head -20
```

**Commit**: `feat(web): add version badge and per-version download to MessageAssistant`

---

## Requirement Traceability

| Requirement ID | Tasks |
|----------------|-------|
| ISR-01 | T7, T8, T12, T13 |
| ISR-02 | T7, T8, T9, T13 |
| ISR-03 | T10, T11, T5, T13 |
| ISR-04 | T7, T10, T11 |
| ISR-05 | T1, T2, T5 |
| ISR-06 | T3, T4, T12 |
| ISR-07 | T10 |
| ISR-08 | T6, T14, T15 |
| ISR-09 | T15 |

**Coverage**: 9 requirements → 15 tasks mapeados

---

## Granularity Check

| Task | Escopo | Status |
|------|--------|--------|
| T1: Migrations SQL | 2 arquivos (par up/down) | ✅ Granular |
| T2: Model GORM | 1 arquivo | ✅ Granular |
| T3: Repository method | 1 arquivo | ✅ Granular |
| T4: DispatchPayload field | 1 arquivo | ✅ Granular |
| T5: CompleteBody + complete.go | 2 arquivos acoplados | ✅ Aceitável (contrato + persistência) |
| T6: BuildContentZip + handler + rota | 3 arquivos acoplados (service + handler + wire) | ✅ Aceitável (vertical slice do endpoint) |
| T7: state.py fields | 1 arquivo | ✅ Granular |
| T8: detect_intent prompt + node | 2 arquivos (prompt + nó) | ✅ Aceitável (prompt é dependência direta do nó) |
| T9: edit_slides prompt + node | 2 arquivos (prompt + nó) | ✅ Aceitável (prompt é dependência direta do nó) |
| T10: upload_assets extension | 1 arquivo | ✅ Granular |
| T11: finalize extension | 1 arquivo | ✅ Granular |
| T12: post_message update | 1 arquivo | ✅ Granular |
| T13: graph.py rewire | 1 arquivo | ✅ Granular |
| T14: downloadContentZip | 1 arquivo | ✅ Granular |
| T15: MessageAssistant + ChatThread | 2 arquivos acoplados | ✅ Aceitável (prop + consumo) |
