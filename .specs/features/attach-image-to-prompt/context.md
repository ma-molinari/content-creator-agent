# Anexar Imagem ao Prompt — Context

**Gathered:** 2026-05-05
**Spec:** `.specs/features/attach-image-to-prompt/spec.md`
**Status:** Pronto para Design

---

## Feature Boundary

Anexar 1 a 4 imagens (JPEG/PNG/WEBP, ≤ 5MB cada) ao composer e enviá-las junto com o texto em uma única requisição. As imagens são persistidas no S3, vinculadas à mensagem do usuário, e disponibilizadas ao worker LangGraph que as incorpora aos slides conforme a intenção do prompt — com fallback para "capa/entrada" no slide 1 quando o usuário não especifica uso. Mantém retrocompatibilidade com mensagens só-texto. Inclui limpeza S3 ao deletar/evictar chat. Suporta tanto primeiro turno quanto refinamento (P2).

---

## Implementation Decisions

### Quantidade de anexos por mensagem

- **Múltiplas** imagens permitidas por mensagem.
- **Teto MVP: 4 imagens** (decisão da agente — ver "Agent's Discretion").
- Validação client-side antes do envio; servidor valida novamente como segunda camada.

### Exibição na bolha do usuário (chat thread)

- Sim: thumbnails ficam **dentro da bolha do usuário**, acima do texto.
- Click no thumbnail abre **lightbox** (mesmo padrão visual do `SlideViewer`).
- Imagens persistem após reload (URL fresca via padrão já usado em `useFiles` para slides).

### Timing do upload

- Upload acontece **junto com o envio** (clique em Enviar).
- **Uma única requisição** `multipart/form-data` para `POST /chats/:id/messages`.
- Sem upload em background / pre-signed PUT do client (decisão simplifica V1; pode evoluir em V2).

### Validações e limites

- **Formatos aceitos**: `image/jpeg`, `image/png`, `image/webp` (padrão do projeto, mesmo de `user_profile_references`).
- **Tamanho máximo**: 5 MB por imagem (padrão do projeto).
- **Quantidade máxima**: 4 imagens por mensagem.
- **Validação do mime real** no servidor (sniff dos primeiros bytes), não confiar no `Content-Type` enviado pelo cliente.
- **Nome do arquivo** descartado: chave S3 = UUID + extensão derivada do mime real.

### Comportamento no worker

- Worker recebe lista de chaves S3 dos anexos no `DispatchPayload`.
- Texto do usuário **menciona uso explícito** ("use no slide X", "como fundo da capa") → worker aplica conforme.
- Texto **sem instrução** → primeira imagem vira **capa/entrada do slide 1** (visual dominante: hero/fundo/destaque, à discrição visual do agente respeitando a marca).
- Imagens adicionais sem instrução → distribuídas como visual de apoio, à discrição do agente.
- Imagens são incorporadas via **URL pública/presignada** no HTML (não inline base64) para manter o HTML leve para o Playwright.

### Comportamento no fluxo de refinamento (P2)

- Anexar imagem em mensagem de refinamento é permitido (não bloqueia).
- Aplica-se conforme instrução textual; sem instrução → atualiza slide 1 (capa) preservando demais slides existentes.
- Anexos do usuário **persistem** em refinamentos (não são apagados quando o assistente edita).

### Limpeza S3

- Ao **deletar chat** (`DELETE /chats/:id`): anexos do usuário entram no `CollectS3KeysForChat` (ou novo helper equivalente) junto com `s3_key` (JPEG slides) e `html_s3_key` (HTML slides).
- Ao **evictar chat** (criação do 6º chat): mesma cobertura.
- Best-effort: falha parcial no S3 não impede sucesso da operação principal (mantém padrão atual).

### Tratamento de erro

- Texto vazio + imagens → bloqueia (mantém regra atual `ErrEmptyPrompt`).
- Erro de upload S3 → **falha antes** de criar `ChatContent` ou `Job`; sem mensagem órfã.
- Erro de visão/LLM no worker → job marcado como `failed` com mensagem clara; **não** gerar slides ignorando a imagem silenciosamente.
- Composer preserva texto + anexos válidos em qualquer erro do envio (não limpa o draft).

### Modelo de dados (direção)

- Nova tabela dedicada para anexos do usuário (proposta: `chat_content_attachment`) ligada por FK a `chat_content`, com `ON DELETE CASCADE`. Decisão final do schema fica para Design.
- Por que não reaproveitar `chat_content_image`? Porque essa tabela tem `slide_number NOT NULL` e semântica de "JPEG de slide gerado pelo assistente"; misturar quebraria queries como `CollectS3KeysForChat` e `GetLatestAssistantHTMLKeys`.

### Indicador de progresso (P3)

- `JobStatusIndicator` ganha label adicional "Aplicando imagens anexadas…" quando o job tem anexos (somente polish; pode ficar fora do MVP se Design considerar não trivial).

### Agent's Discretion

- **Teto de 4 imagens por mensagem**: alinhado a tamanho típico de carrossel curto e custo de tokens em chamadas multimodais; revisável após dados de uso.
- **Distribuição das imagens 2-N quando sem instrução**: ordem e papel ficam a critério do agente (visual de apoio em slides intermediários ou referência conceitual no rascunho do slide). Spec só amarra a #1 = capa.
- **Layout exato do thumbnail na bolha**: dentro da bolha, acima do texto, em grid horizontal com ratio preservado; estilo final segue `ui-guidelines.md` na fase Design.
- **Estratégia técnica para o worker carregar a imagem (download bytes vs URL direta no HTML, pré-render no LLM via vision API)**: decidida em Design com base no provider e custo.

---

## Specific References

- **UX de mercado**: ChatGPT, Claude, Gemini — botão de clipe à esquerda do textarea, thumbnails inline acima do composer, **×** para remover antes de enviar.
- **Padrão interno do projeto**: validações, tipos e tamanho seguem `user_profile_references` (referências de marca já existentes em `/profile`).
- **Renderização Playwright**: o HTML final precisa carregar imagens via URL HTTP(S) presignada, não base64 (o pipeline `render_to_jpeg` já faz isso para Google Fonts; aplicar mesmo princípio para anexos).
- **Eviction e delete**: seguir `service.go` linhas em torno de `CollectS3KeysForChat` + `store.DeleteMany` (`apps/api/internal/chat/service.go`).

---

## Deferred Ideas

| Ideia | Motivo do adiamento | Fase alvo |
|-------|---------------------|-----------|
| Editor de imagem no client (crop, redimensionar, filtros) | UX adicional grande, fora do escopo MVP | V2 |
| Pre-signed PUT (upload direto do client ao S3 sem passar pela API) | Otimização de banda; complica auth e limites; não é gargalo no V1 | V2 |
| Substituir/remover anexo após envio | Exige conceito de mensagens editáveis (não existe) | V2 |
| Galeria de anexos reutilizáveis entre chats | Exige domínio próprio e UI nova | V2 |
| Anexar áudio/vídeo/PDF | Escopo desta feature é só imagem | V2 |
| Variações geradas a partir da imagem (img2img) | Depende de provider novo; pipeline atual é HTML→JPEG | V2 |
| Ampliar o teto de 4 para 8 imagens com base em dados | Decidir só após métricas reais de uso | V2 |
