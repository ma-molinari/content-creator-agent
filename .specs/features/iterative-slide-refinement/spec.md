# Iterative Slide Refinement — Especificação

**Data**: 2026-05-03
**Status**: Aprovado — aguardando design

---

## Problem Statement

Após a geração inicial de slides em um chat, cada novo prompt regenera o layout do zero, descartando todo o trabalho visual anterior. O usuário que quer apenas ajustar um texto, cor ou elemento específico é forçado a aceitar um layout completamente diferente ou repetir instruções detalhadas de identidade visual a cada prompt. Isso gera frustração e desperdiça tokens.

## Goals

- [ ] Permitir refinamento incremental de slides dentro do mesmo chat, preservando o layout e identidade visual gerados
- [ ] O sistema detecta automaticamente a intenção do prompt: editar slides existentes vs. criar novos do zero
- [ ] Manter histórico de versões por chat para que o usuário possa baixar qualquer versão anterior
- [ ] Reduzir tokens de saída em prompts de refinamento (o LLM edita HTML existente em vez de gerar do zero)

## Out of Scope

| Feature | Motivo |
|---------|--------|
| Diff visual "antes vs. depois" por slide | Complexidade de UI — V2 |
| Rollback automático (restaurar versão anterior no editor) | Download manual da versão anterior cobre o caso V1 |
| Edição slide a slide com seleção no frontend | V2 — requer UI de edição granular |
| Controle explícito de modo (toggle "editar / criar novo") | Intent detection automático cobre o caso — revisitar se houver falsos positivos |

---

## User Stories

### P1: Refinamento incremental de slides — MVP

**User Story**: Como usuário, quero enviar um novo prompt em um chat que já tem slides gerados e que o sistema aplique as minhas mudanças nos slides existentes, preservando o layout, para que eu possa iterar sem perder o trabalho visual anterior.

**Por que P1**: É o núcleo da feature. Sem isso, o problema de frustração não é resolvido.

**Acceptance Criteria**:

1. WHEN um chat já possui slides gerados e o usuário envia um novo prompt com intenção de refinamento THEN o worker SHALL receber os HTMLs da versão mais recente como contexto e editá-los em vez de gerar do zero
2. WHEN o worker detecta que o prompt é sobre um tema completamente diferente ou uma criação nova THEN o worker SHALL ignorar os HTMLs existentes e gerar slides novos do zero
3. WHEN o job de refinamento é concluído THEN os novos slides (JPEG + HTML fonte) SHALL ser armazenados no S3 vinculados a uma nova versão
4. WHEN o refinamento é concluído THEN a resposta do assistente no thread SHALL exibir os slides atualizados no lugar da mensagem correspondente
5. WHEN o HTML fonte de uma versão é armazenado no S3 THEN ele SHALL ser recuperável pelo worker na próxima iteração via chave S3 registrada no banco

**Independent Test**: Gerar slides sobre "arrays vs listas", depois enviar "muda o título para negrito vermelho" — os slides resultantes devem manter o layout original com apenas o título alterado.

---

### P1: Armazenamento do HTML fonte por versão

**User Story**: Como sistema, quero armazenar o HTML fonte de cada geração de slides no S3, para que versões futuras possam ser editadas e versões antigas possam ser disponibilizadas para download.

**Por que P1**: Dependência direta do refinamento — sem o HTML fonte armazenado não há contexto para edição.

**Acceptance Criteria**:

1. WHEN o worker finaliza a geração ou edição de slides THEN o callback SHALL incluir as chaves S3 dos arquivos HTML fonte de cada slide
2. WHEN a API recebe o callback com sucesso THEN ela SHALL persistir as chaves S3 dos HTMLs associadas ao `ChatContent` da resposta
3. WHEN um novo job é criado para um chat com slides existentes THEN a API SHALL incluir no payload de dispatch ao worker as chaves S3 (ou o conteúdo) dos HTMLs da versão mais recente
4. WHEN o HTML fonte é armazenado no S3 THEN o Content-Type SHALL ser `text/html` e a chave SHALL seguir o padrão `slides/{userID}/{chatID}/{jobID}/slide_{n}.html`

**Independent Test**: Após geração, verificar no S3 a existência dos arquivos `.html` com o conteúdo correto para cada slide.

---

### P2: Download por versão no thread

**User Story**: Como usuário, quero poder baixar os slides de qualquer versão anterior diretamente da mensagem correspondente no thread do chat, para que eu possa recuperar um estado anterior caso não esteja satisfeito com as edições.

**Por que P2**: Importante para a usabilidade do histórico de versões, mas o usuário já consegue visualizar versões no thread — o download é o diferencial.

**Acceptance Criteria**:

1. WHEN cada mensagem de assistente com slides é exibida no thread THEN ela SHALL ter um botão de download individual para os slides daquela versão
2. WHEN o usuário clica em download de uma versão específica THEN o sistema SHALL baixar um ZIP contendo os JPEGs daquela versão (não de todas as versões do chat)
3. WHEN uma versão é mais antiga que a mais recente THEN ela SHALL ser visualmente identificável no thread (ex.: label "Versão anterior") para que o usuário saiba que não é a atual

**Independent Test**: Gerar slides em 3 rounds; clicar em download na mensagem do round 1 — o ZIP deve conter apenas os slides do round 1.

---

## Edge Cases

- WHEN o chat possui mensagens mas nenhum slide gerado ainda THEN o worker SHALL tratar como primeira geração (sem contexto de HTML)
- WHEN o S3 retorna erro ao recuperar HTML fonte de versão anterior THEN o worker SHALL logar o erro e proceder com geração do zero, informando no log `job_id` e `reason=html_fetch_failed`
- WHEN o HTML fonte de uma versão está corrompido ou vazio THEN o worker SHALL proceder com geração do zero (fallback seguro)
- WHEN o prompt de refinamento resulta em um número diferente de slides THEN o worker SHALL gerar os slides com o novo total (não forçar o mesmo número)
- WHEN o job é de um chat com um único round anterior THEN o comportamento é idêntico ao caso de múltiplos rounds (sem lógica especial)

---

## Requirement Traceability

| Requirement ID | Story | Fase | Status |
|----------------|-------|------|--------|
| ISR-01 | P1: Refinamento incremental — worker recebe HTML existente | Design | Pending |
| ISR-02 | P1: Refinamento incremental — detecção de intenção (editar vs. novo) | Design | Pending |
| ISR-03 | P1: Refinamento incremental — resultado salvo como nova versão | Design | Pending |
| ISR-04 | P1: Armazenamento HTML fonte no S3 via callback | Design | Pending |
| ISR-05 | P1: API persiste chaves S3 dos HTMLs por ChatContent | Design | Pending |
| ISR-06 | P1: API inclui HTMLs existentes no payload de dispatch | Design | Pending |
| ISR-07 | P1: Convenção de chave S3 para HTML fonte | Design | Pending |
| ISR-08 | P2: Download por versão no thread | Design | Pending |
| ISR-09 | P2: Identificação visual de versão anterior no thread | Design | Pending |

**Coverage:** 9 requirements, 0 mapeados a tasks, 9 pendentes de design

---

## Success Criteria

- [ ] Um prompt de refinamento ("ajusta a cor", "muda o título", "deixa o texto mais curto") não altera o layout dos slides — apenas o elemento pedido muda
- [ ] Um prompt de nova criação ("cria slides sobre Python") em um chat com slides existentes gera slides completamente novos sem conflito
- [ ] Cada versão gerada tem seus HTMLs fonte disponíveis no S3 e recuperáveis pelo worker
- [ ] O usuário consegue baixar slides de qualquer versão anterior no thread
- [ ] Nenhuma geração anterior é perdida — o thread mantém histórico completo
