# Anexar Imagem ao Prompt — Especificação

## Problem Statement

Hoje o usuário só consegue descrever em texto a imagem que quer no slide. Para um post de Instagram (especialmente o slide de capa), ter a imagem real acelera a curadoria visual e elimina a necessidade de ele descrever em palavras algo que já existe (foto de produto, print, screenshot, ilustração). Agentes de mercado (ChatGPT, Claude, Gemini) já oferecem anexar imagem como interação básica do composer.

## Goals

- [ ] Usuário consegue anexar imagens (até **4 por mensagem**) no `ComposerBar` e enviá-las junto com o texto em uma única ação, semelhante a agentes de mercado.
- [ ] As imagens anexadas são usadas pelo worker na geração dos slides conforme a instrução textual; sem instrução explícita, a imagem é incorporada ao **slide 1** como capa/entrada.
- [ ] Excluir o chat (ou ele ser removido por eviction) também remove os anexos do usuário do bucket S3 — sem leftovers.

## Out of Scope

| Feature | Razão |
| ----------- | -------------- |
| Editor de imagem no client (crop, filtros, redimensionar) | V2 — UX adicional; entrega depende de stack visual maior |
| Remover/substituir anexo após envio | V2 — exige conceito de mensagens editáveis, não existe hoje |
| Anexar áudio, vídeo, PDF ou outros formatos | V2 — escopo desta feature é só imagem |
| Biblioteca/galeria de anexos reutilizáveis entre chats | V2 — não há padrão de reuso ainda |
| Geração de variações da imagem anexada (img2img) | V2 — depende de provider de imagem novo (não é o caso do projeto, que usa HTML→JPEG) |
| Anexar imagem de referência de marca pelo composer | Já existe via `/profile` (referências de design), domínio separado |

---

## User Stories

### P1: Anexar e enviar imagens junto com o texto — MVP

**User Story**: Como criador de conteúdo, quero anexar imagens ao prompt diretamente do composer, junto com o texto da mensagem, para que os slides gerados usem essas imagens conforme minha intenção.

**Why P1**: É o núcleo da feature. Sem isso nada do resto faz sentido.

**Acceptance Criteria**:

1. WHEN o usuário clica no ícone/botão de anexar no `ComposerBar` THEN o sistema SHALL abrir o seletor nativo de arquivos restrito a `image/jpeg, image/png, image/webp`.
2. WHEN o usuário seleciona uma ou mais imagens válidas (até 4 no total, cada uma ≤ 5MB) THEN o sistema SHALL mostrar thumbnails das imagens dentro/acima do campo de texto, cada thumbnail com botão **×** para remover antes de enviar.
3. WHEN o usuário tenta anexar uma imagem com formato fora de `JPEG|PNG|WEBP`, ou maior que 5MB, ou que ultrapassaria o limite de 4 anexos THEN o sistema SHALL bloquear a adição e exibir uma mensagem clara via toast (sem perder os anexos já válidos nem o texto digitado).
4. WHEN o usuário clica **Enviar** com texto válido + anexos selecionados THEN o sistema SHALL enviar tudo em **uma única requisição** (`multipart/form-data`) ao endpoint de mensagens do chat.
5. WHEN a requisição é aceita pela API THEN ela SHALL retornar **202 + jobId** mantendo o contrato atual de jobs assíncronos.
6. WHEN o envio falha (validação, rede, dispatch) THEN o sistema SHALL preservar texto + anexos no composer (não limpar o draft) e exibir erro localizado.

**Independent Test**: Anexar 2 imagens válidas + texto "use a primeira como capa" → enviar → ver 202 + jobId; rejeitar GIF de 3MB; rejeitar JPEG de 8MB; rejeitar 5ª imagem.

---

### P1: Imagens aparecem na bolha do usuário no thread

**User Story**: Como criador de conteúdo, quero ver as imagens que enviei dentro da minha bolha de mensagem no chat, para confirmar visualmente o que foi anexado e ter histórico claro do meu pedido.

**Why P1**: Sem isso o usuário perde rastreabilidade do que enviou (sai da tela e some). É padrão de mercado.

**Acceptance Criteria**:

1. WHEN o servidor responde 202 e a mensagem aparece no thread THEN o sistema SHALL renderizar as imagens anexadas como thumbnails dentro da bolha do usuário (acima do texto), com aspect ratio preservado.
2. WHEN o usuário clica em um thumbnail THEN o sistema SHALL abrir a imagem em lightbox (mesmo padrão de visualização dos slides).
3. WHEN a página é recarregada e o histórico do chat é recuperado THEN as imagens da bolha SHALL continuar visíveis (URLs frescas).
4. WHEN uma imagem da bolha não consegue carregar (URL expirada, 403) THEN o sistema SHALL mostrar placeholder com ícone de "imagem indisponível" sem quebrar o layout.

**Independent Test**: Enviar mensagem com 2 imagens → ver bolha com thumbnails → clicar abre lightbox → recarregar página → thumbnails continuam OK.

---

### P1: Worker usa as imagens conforme intenção do prompt

**User Story**: Como criador de conteúdo, quero que minha imagem anexada seja efetivamente incorporada nos slides gerados conforme o que pedi no texto, e que sem instrução explícita ela vire o visual da capa.

**Why P1**: É o "porquê" da feature. Anexar sem aplicar é inútil.

**Acceptance Criteria**:

1. WHEN o worker recebe um job com anexos do usuário e o texto do usuário **menciona explicitamente** onde/como usar a imagem (ex.: "use no slide 3", "como fundo da capa", "ao lado do parágrafo X") THEN o worker SHALL aplicar a(s) imagem(ns) seguindo essa instrução durante a geração dos slides.
2. WHEN o worker recebe anexos mas o texto **não menciona** uso explícito THEN o worker SHALL incorporar a primeira imagem ao slide 1 como **capa/entrada** (visual dominante: hero, fundo, ou destaque); imagens adicionais (se houver) SHALL ser distribuídas como visual de apoio nos slides seguintes ou referenciadas no escopo, à discrição do agente.
3. WHEN o worker gera o HTML do slide THEN as imagens anexadas SHALL ser servidas via URL pública/presignada (não inline em base64) para manter o HTML leve e renderizável pelo Playwright.
4. WHEN as imagens são incorporadas em um slide THEN o JPEG renderizado pelo Playwright SHALL conter a imagem visível (sem placeholder de "imagem quebrada").

**Independent Test**: Job 1 — texto "tutorial sobre Postgres" + 1 imagem sem instrução → slide 1 tem a imagem como hero/fundo. Job 2 — texto "use a foto no slide 3" + 1 imagem → slide 3 tem a imagem.

---

### P1: Limpeza S3 ao excluir / fazer eviction do chat

**User Story**: Como operador, quero que excluir um chat também remova do bucket S3 todas as imagens anexadas pelo usuário a esse chat, para evitar storage órfão e custo crescente.

**Why P1**: Já é regra do projeto para slides JPEG/HTML (`CollectS3KeysForChat` + `DeleteMany`). Anexos do usuário sem essa cobertura deixariam buracos de storage e potencialmente vazariam dados após o usuário deletar.

**Acceptance Criteria**:

1. WHEN o usuário deleta um chat via `DELETE /chats/:id` THEN o sistema SHALL deletar do bucket S3 todas as imagens anexadas pelo usuário pertencentes a esse chat, na mesma operação que já deleta JPEGs e HTMLs dos slides.
2. WHEN o limite de 5 chats por usuário força eviction (ao criar o 6º) THEN o sistema SHALL incluir os anexos do chat removido na limpeza S3 já existente para o chat evictado.
3. WHEN a deleção do S3 falha parcialmente THEN o sistema SHALL manter o comportamento atual (best-effort, log do erro) sem impedir o sucesso da operação principal.

**Independent Test**: Criar chat com 2 mensagens contendo imagens → confirmar 4 keys no bucket → `DELETE /chats/:id` → verificar bucket vazio dos prefixos do chat.

---

### P2: Refinamento mantém suporte a imagem anexada

**User Story**: Como criador de conteúdo, em mensagens de refinamento (chat já tem slides), quero também poder anexar imagens e ter elas aplicadas conforme meu pedido.

**Why P2**: O fluxo MVP cobre primeiro turno. Refinamento amplia, mas sem ele a feature ainda entrega valor isolado.

**Acceptance Criteria**:

1. WHEN o chat já tem slides assistente e o usuário envia uma nova mensagem com anexo THEN o sistema SHALL aceitar o anexo no mesmo formato do P1 (multipart, mesmas validações).
2. WHEN o worker detecta refinamento e há anexo + instrução explícita ("substitua a imagem do slide X pela anexada") THEN o worker SHALL aplicar conforme a instrução durante a edição dos slides existentes.
3. WHEN o worker detecta refinamento e há anexo **sem** instrução explícita THEN o worker SHALL atualizar o **slide 1 (capa)** existente para incorporar a nova imagem como visual dominante, preservando demais slides.
4. WHEN o callback do worker conclui o refinamento THEN as imagens anexadas pelo usuário **continuam acessíveis** na bolha do usuário do thread (não são apagadas pelo refinamento).

**Independent Test**: Em chat com 5 slides, enviar "troque a capa" + 1 imagem → ver slide 1 atualizado, slides 2-5 preservados, bolha do usuário com thumbnail.

---

### P3: Indicador de progresso durante a geração com anexos

**User Story**: Como criador de conteúdo, quero feedback claro de que minhas imagens foram recebidas e estão sendo usadas, durante o processamento do job.

**Why P3**: Polish. O `JobStatusIndicator` atual já cobre o estado processing/done/failed; um label específico ajuda mas não é essencial.

**Acceptance Criteria**:

1. WHEN o job está em processamento e a mensagem tem anexos THEN o `JobStatusIndicator` SHALL exibir label adicional "Aplicando imagens anexadas…" ou equivalente durante a fase relevante.

---

## Edge Cases

- WHEN o usuário envia uma mensagem **somente com imagem(ns) e texto vazio** THEN o sistema SHALL rejeitar com erro `texto obrigatório` (mantém regra atual `SanitizeUserInput → ErrEmptyPrompt`); o composer não permite Enviar com texto vazio.
- WHEN um anexo passa a validação client-side mas o S3 retorna erro durante o upload THEN o sistema SHALL falhar a requisição **antes** de criar `ChatContent` ou `Job` (sem persistir mensagem órfã) e exibir erro localizado preservando o draft.
- WHEN o LLM/visão falha em interpretar a imagem (timeout, erro do provider) THEN o worker SHALL marcar o job como `failed` com mensagem clara ("não foi possível processar a imagem anexada"); não SHALL gerar slides ignorando a imagem silenciosamente.
- WHEN o nome original do arquivo contém caracteres especiais ou path traversal THEN o sistema SHALL gerar uma chave S3 segura usando UUID + extensão validada do mime real (não confiar no filename do client).
- WHEN o usuário tenta arrastar 10 imagens para o composer THEN o sistema SHALL aceitar somente as 4 primeiras válidas e exibir toast informando o limite (sem rejeitar tudo).
- WHEN a imagem anexada tem dimensões muito grandes (ex.: 8000×6000) THEN o sistema SHALL aceitar (validação é só por bytes ≤ 5MB e mime); o worker pode redimensionar internamente se a renderização Playwright pesar.
- WHEN um chat é evictado pelo limite de 5 e tem anexos THEN os anexos SHALL ser incluídos na coleção S3 já feita por `CollectS3KeysForChat`, sem leak.

---

## Requirement Traceability

| Requirement ID | Story            | Phase  | Status  |
| -------------- | ---------------- | ------ | ------- |
| AIP-01         | P1: Anexar/Enviar | Design | Pending |
| AIP-02         | P1: Anexar/Enviar | Design | Pending |
| AIP-03         | P1: Anexar/Enviar | Design | Pending |
| AIP-04         | P1: Bolha thread  | Design | Pending |
| AIP-05         | P1: Worker usa    | Design | Pending |
| AIP-06         | P1: Worker usa    | Design | Pending |
| AIP-07         | P1: Limpeza S3    | Design | Pending |
| AIP-08         | P2: Refinamento   | -      | Pending |
| AIP-09         | P3: Progress      | -      | Pending |

**Coverage:** 9 IDs propostos; mapeamento detalhado para tasks acontece na fase Tasks.

### Resumo do que cada ID cobre

- **AIP-01**: Botão de anexar + seletor de arquivos restrito a JPEG/PNG/WEBP no `ComposerBar`.
- **AIP-02**: Validação client-side (tipo, tamanho ≤ 5MB, máx 4 anexos) + thumbnails com remover.
- **AIP-03**: Envio multipart único (texto + anexos) → 202 + jobId; preservação do draft em erro.
- **AIP-04**: Persistência dos anexos vinculados a `ChatContent` do usuário; thumbnails na bolha; lightbox; URLs frescas.
- **AIP-05**: Worker aplica imagens conforme instrução explícita do texto.
- **AIP-06**: Sem instrução → primeira imagem vira capa do slide 1; demais à discrição (apoio).
- **AIP-07**: `CollectS3KeysForChat` (ou equivalente) inclui anexos do usuário; eviction + delete cobrem.
- **AIP-08**: Mesmo fluxo no caminho de refinamento (`edit_slides`).
- **AIP-09**: Label adicional no `JobStatusIndicator` quando há anexos.

---

## Success Criteria

Como sabemos que a feature foi entregue com sucesso:

- [ ] Anexar 1–4 imagens válidas + texto + Enviar funciona end-to-end e gera slides com as imagens visíveis (não placeholders) em ≤ tempo médio dos jobs atuais + 30%.
- [ ] Validações client-side rejeitam 100% dos casos inválidos (formato, tamanho, contagem) com mensagens claras antes do envio.
- [ ] Mensagem do usuário no thread mostra thumbnails das imagens enviadas, persistente após reload.
- [ ] Sem instrução de uso, a primeira imagem aparece na capa do slide 1 em ≥ 80% dos jobs (avaliação manual em N=10 prompts variados).
- [ ] `DELETE /chats/:id` remove **todos** os anexos do usuário do bucket S3 (verificação no bucket: zero leftovers para o prefixo do chat).
- [ ] Eviction (criar 6º chat) também remove anexos do chat evictado.
- [ ] Falhas de upload S3 ou de visão no worker resultam em estado coerente (job `failed` com mensagem útil; sem mensagem órfã no chat).
