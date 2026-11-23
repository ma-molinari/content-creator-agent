# Fidelidade visual — plano de tarefas

**Status:** proposta para revisão; nenhuma tarefa implementada.  
**Design e requisitos:** `docs/TDD-FIDELIDADE-VISUAL.md`.  
**Referência anterior:** `.specs/features/hybrid-post-generation/tasks.md` e `validacao.md`.  
**Responsável:** responsável pelo projeto; sem ticket ou prazo informado.

Este plano usa as seções do TDD como identificadores de requisitos, sem criar um segundo contrato. `[P]` indica elegibilidade técnica após as dependências, não autorização para iniciar agentes. As tarefas são de tamanho médio; arquivos de contrato, grafo, schema e fixtures compartilhados exigem coordenação antes de execução paralela. Cada tarefa termina com validação proporcional e commit atômico em português, sem assinatura GPG conforme a preferência já informada.

Antes de implementar, leia a seção do TDD indicada, inspecione os arquivos e testes existentes e preserve os formatos `legacy_html` e `structured_v1`. `postFormat` continua identificando a família de fluxo; `schemaVersion` identifica o documento. O TDD é proposta, não comportamento já entregue.

**Decisões e gates:** T01 fecha medidas de barras/linhas, política de contraste, tratamento de referências conflitantes, limite de cache e operação de inserção com o responsável. Protótipos exploratórios fora das tarefas podem ser preparados antes desse fechamento, mas as dependências abaixo bloqueiam o início formal das tarefas dependentes e não permitem congelar contrato/renderer ou ativar V2. A T01 deve entregar amostras concretas para revisão antes de solicitar o aceite. A T18 da geração híbrida e o aceite visual e operacional são pré-requisitos de ativação, não de desenvolvimento ou testes isolados. Não inventar metas de negócio nem tratar amostras sintéticas como aceite de marca real.

## Dependências e execução

```text
T01 → T02
T02 → T03, T05, T09
T01 + T02 → T04
T01 → T06
T02 + T05 + T06 → T07
T04 + T07 → T08
T03 + T09 → T10
T08 + T09 → T11
T09 + T10 + T11 → T12
T08 + T10 + T12 → T13
T13 → T14
T18 híbrida + aceite operacional → ativação de V2
```

O diagrama é resumido; as listas **Dependências** de cada tarefa são autoritativas. Os gates de aceite humano da T01 bloqueiam a conclusão e o início formal das tarefas dependentes, mas um contrato ou protótipo explicitamente provisório pode ser preparado fora delas para tornar a revisão concreta. T03, T04, T05, T06 e T09 podem ser preparadas em paralelo após seus respectivos gates, coordenando as fixtures e módulos em comum. T10 não habilita seleção de V2. T08 não anuncia capacidade V2 até T11. T12 só habilita a seleção mediante flag e negociação; a flag permanece desligada por padrão. Uma cadeia longa é T01 → T02 → T05 → T07 → T08 → T11 → T12 → T13 → T14; o diagrama não estima duração.

## Comandos-base de validação

Os comandos abaixo são pontos de partida; cada executor deve selecionar os testes afetados e preparar as dependências descritas em `docs/TESTING.md`. Integração Go requer PostgreSQL e configuração de teste; o teste visual requer Chromium e fontes. Não usar credenciais reais em testes unitários.

```powershell
Push-Location apps/worker
python -m pytest tests/test_post_document.py tests/test_post_operations.py tests/test_contract_parity.py -q
Pop-Location

Push-Location apps/api
go test ./...
go test -tags=integration ./integration/...
Pop-Location
```

Para o ensaio visual e E2E com serviços externos, seguir os procedimentos opt-in documentados; registrar quando S3 ou LLM forem simulados. A T14 exige ambiente controlado com S3 real e revisão humana.

## Tarefas

### T01 — Catálogo visual e contratos de comportamento

**Objetivo:** documentar o catálogo V2 e fechar as decisões necessárias para implementação verificável.  
**Contexto:** TDD §§4–5, 9 e 12; `apps/worker/app/post_renderer.py`, `post_operations.py` e ensaio em `docs/avaliacoes/2026-11-23-referencias-visuais/`. O sistema atual aceita apenas texto/imagem e três layouts; os limites de quatro decorações e 12 elementos já constam do TDD.  
**Dependências:** nenhuma. **TDD:** §§5.1–5.4, 9 e 12.

**Pronto quando:**

- [x] Existem exemplos revisáveis de barra e linha por largura, espessura, canto, posição e layout, incluindo limites e overflow; os valores de renderização são definidos com o responsável antes do congelamento.
- [x] A política de contraste, inclusive base V1 preexistente e mudanças compartilhadas de token, e a regra de referências ambíguas/conflitantes são decididas e registradas. Expiração/limite do cache e os contratos de operações e capacidade são definidos sem inventar metas de produto.
- [x] Fixtures/contratos provisórios e decisões pendentes são identificados como tal; a aceitação visual do catálogo é registrada antes de declarar a tarefa concluída.

**Aceite:** responsável aprovou a proposta em 23/11/2026. Ver [catálogo e contratos](catalogo-v2-proposta.md) e [amostras](catalogo-v2-proposta.svg). A validação do renderer real e do overflow permanece nas tarefas posteriores.

**Verificar:** revisar amostras 1080×1350, casos limite e decisões com o responsável. **Commit sugerido:** `docs: definir catálogo de destaques visuais`.

### T02 — Documento V2 e promoção determinística [P]

**Objetivo:** definir o contrato Python V2, fixtures compartilhadas e conversão V1→V2 sem mutar a origem.  
**Contexto:** `apps/worker/app/post_document.py`, `tests/fixtures/structured_documents.json`, `apps/worker/tests/test_contract_parity.py`; TDD §5.2. Os consumidores atuais das fixtures validam V1: criar um arquivo V2 separado, por exemplo `tests/fixtures/structured_documents_v2.json`, sem adicionar casos V2 ao conjunto consumido pelo validador V1. A promoção mantém cores literais, inicializa tokens conforme o TDD e não cria decorações.
**Dependências:** T01. **TDD:** §§4–5.2, 9.

**Pronto quando:**

- [x] Schema fechado aceita paleta, referência de token ou hexadecimal e `decoration` nos enums; rejeita extras, campos ambíguos, IDs inválidos/duplicados, mais de quatro decorações ou 12 elementos e limites V1 violados. A validação contextual também rejeita assets não autorizados.
- [x] Conversão preserva IDs, ordem, conteúdo, estilos e assets, inclusive documentos com múltiplos slides, sem texto ou com 12 elementos; resolve defaults de V1 antes da conversão e inicializa tokens conforme o TDD.
- [x] Fixtures V2 compartilháveis têm casos válidos e inválidos, enquanto o arquivo e os consumidores V1 continuam passando sem alterações incompatíveis. A T03 conectará o consumidor Go às novas fixtures. Nenhuma rota de produção passa a gerar V2 nesta tarefa.

**Validação:** 62 testes de contrato e operações V1/V2 passaram no Docker em 23/11/2026.

**Verificar:** testes do schema e fixtures no worker; preparar os casos para a paridade Go da T03. **Commit:** `feat(worker): definir contrato visual v2`.

### T03 — Validador V2 na fronteira Go [P]

**Objetivo:** validar o documento V2 na API com semântica equivalente à do worker.  
**Contexto:** `apps/api/internal/jobs/structured_document.go`, `structured_complete.go`, `structured_contract_test.go`, `structured_complete_test.go`, `tests/fixtures/structured_documents.json`. A API atual chama apenas `validateDocumentV1`; manter limites, `Content-Type`, UTF-8 e validação de manifesto.  
**Dependências:** T02. **TDD:** §§5.2, 6, 8–9.

**Pronto quando:**

- [x] Validador V2 rejeita cores/tokens inválidos, objetos com campos extras, enums/combinações inválidos, limites excedidos e IDs de assets inválidos; retorna o conjunto de IDs para comparar com o manifesto na publicação. Não tratar sintaxe, igualdade de IDs ou prefixo do job como prova da origem autorizada dos bytes.
- [x] Go e Python consomem as mesmas fixtures V2 válidas e inválidas, inclusive casos de JSON estrito; os consumidores e fixtures V1 permanecem funcionais.
- [x] O validador existe sem permitir publicação V2 por jobs V1 ou callback antigo; a integração com schema alvo fica na T10.

**Validação:** fixtures compartilhadas V1/V2 no worker e testes do pacote `internal/jobs` em 23/11/2026.

**Verificar:** testes unitários Go e paridade Python com fixtures compartilhadas. **Commit:** `feat(api): validar documento visual v2`.

### T04 — Renderizador V2 e contraste [P]

**Objetivo:** renderizar paleta e decorações com medidas controladas e resultado coerente com o snapshot.  
**Contexto:** `apps/worker/app/post_renderer.py`, `structured_render.py`, `nodes/contrast_fix.py`, testes de render e browser. Hoje a correção de contraste pode alterar HTML sem alterar o snapshot; V2 não deve repetir silenciosamente esse comportamento.  
**Dependências:** T01, T02. **TDD:** §§4–5.4, 8–9.

**Pronto quando:**

- [x] Tokens e literais são resolvidos; barras/linhas usam somente medidas aprovadas, respeitam ordem, safe area e limites, sem HTML/CSS da LLM nem sobreposição arbitrária.
- [x] Contraste segue a política aprovada e não altera campos não autorizados; quando não for possível preservar o pedido, falha claramente antes de publicar. Emitir eventos categorizados de contraste, overflow e renderização, sem conteúdo privado. Renderer V1 mantém seu comportamento e HTML/JPEG antigos não são regravados.
- [x] Testes com Chromium/fontes fixadas verificam HTML/JPEG, dimensões, clipping, casos limite, imagem herdada e consistência com snapshot, incluindo V1 promovido sem exigir igualdade universal de pixels.

**Validação:** 46 testes de renderer e Chromium passaram no Docker em 23/11/2026, com fonte local de teste.

**Verificar:** suíte de renderer e testes de browser do worker. **Commit:** `feat(worker): renderizar destaques visuais v2`.

### T05 — Operações e preservação na edição V2 [P]

**Objetivo:** aplicar operações tipadas de paleta e decoração de forma atômica.  
**Contexto:** `apps/worker/app/post_operations.py`, `structured_editing.py` e testes existentes. `set_text_style` atual substitui o estilo completo; mudanças locais devem preservar os demais campos.  
**Dependências:** T01, T02. **TDD:** §§4–5.3, 9.

**Pronto quando:**

- [x] Operações definidas na T01 incluem alteração de token, inserção em posição válida, atualização e remoção de decoração; IDs e referências são validados e o documento inteiro é revalidado antes do retorno.
- [x] Token compartilhado altera seus consumidores apenas quando isso corresponde à intenção; cores literais promovidas não mudam implicitamente. Token sem consumidores não pode ser apresentado como mudança visual; alvos ambíguos geram reformulação.
- [x] Casos de tipos incorretos, IDs duplicados/inexistentes, limite de 12 elementos, falha parcial e preservação dos campos não envolvidos não publicam resultado; testes também cobrem o limite de interpretação da LLM.

**Validação:** 41 testes de operações, documentos e planner V1 passaram no Docker em 23/11/2026. O aplicador valida operações, não infere intenção; o planner V2 e os casos de interpretação são integrados na T07.

**Verificar:** testes de operações e planner com schema V1/V2. **Commit:** `feat(worker): editar paleta e decorações`.

### T06 — Extração visual estruturada e cache [P]

**Objetivo:** produzir direção visual validada sem perder referências silenciosamente ou compartilhar cache entre usuários.  
**Contexto:** `apps/worker/app/nodes/describe_references.py`, `profile_overview.py`, `apps/worker/prompts/describe_references.md`; o cache atual usa apenas a sequência de chaves, embora o resumo dependa de AUDIT/BRAND. Preservar limite atual de oito imagens na V2.  
**Dependências:** T01. **TDD:** §§5.1, 8–10.

**Pronto quando:**

- [x] A saída tem schema fechado para paleta, barras/linhas e estado observado/incerto; dados inválidos ou referências indisponíveis/parciais seguem a falha clara do TDD, sem tratar confiança do modelo como certeza. Registrar duração, resultado e motivo categorizado da extração, sem conteúdo privado.
- [x] Cache é delimitado e isolado por usuário, identidade/ordem das imagens e versão de schema/prompt/modelo; se usar textos do perfil, inclui esses insumos. Falhas e saídas incompletas não são cacheadas como sucesso.
- [x] Sem referências, criação pode usar o perfil; reanálise explícita sem referências falha claramente. O contrato isolado permite edição V2 independente sem consultar as referências originais; a ligação efetiva do grafo e dos assets herdados é responsabilidade da T08.

**Validação:** sete testes de extração simulada, leitura de referências e cache passaram no Docker em 23/11/2026. A extração V2 não usa AUDIT/BRAND; estes permanecem entrada independente do gerador.

**Verificar:** testes de visão simulada, falhas de S3, mais de oito referências, cache/isolamento, alteração de perfil e ausência de conteúdo sensível nos logs. **Commit:** `feat(worker): estruturar direção visual`.

### T07 — Planejamento de criação e edição V2

**Objetivo:** conectar a direção visual e o schema alvo aos prompts e planos de geração/edição sem alterar V1.  
**Contexto:** `apps/worker/app/structured_generation.py`, `structured_editing.py`, `post_operations.py` e testes correspondentes. A LLM atualmente recebe schema V1, perfil e IDs autorizados.  
**Dependências:** T02, T05, T06. **TDD:** §§5.1–5.3, 6, 8–9.

**Pronto quando:**

- [x] Geração V2 recebe paleta/direção validada e schema correspondente; V1 continua com contrato atual. A direção é orientação, não promessa de reproduzir literalmente a referência.
- [x] Edição V2 recebe a base promovida quando aplicável e as operações da T05; só recebe direção das referências atuais quando o pedido exigir reaplicá-las. Pedido não representável retorna erro de reformulação.
- [x] Testes verificam payloads sem segredos, limites, assets, ausência de referência, retentativa limitada e preservação; uma fixture determinística com barra observada gera operação/documento correspondente.

**Validação:** 23 testes de geração, edição e operações com LLM simulada passaram no Docker em 23/11/2026.

**Verificar:** testes de geração e edição do worker com LLM simulada. **Commit:** `feat(worker): planejar criação e edição visual v2`.

### T08 — Execução V2, upload e endpoint dedicado

**Objetivo:** executar o pipeline V2 e expor uma rota que não possa ser confundida com o endpoint de worker V1.  
**Contexto:** `apps/worker/app/graph.py`, `state.py`, `job_payload.py`, `main.py`, `nodes/structured_pipeline.py`, `structured_render.py`, `structured_upload.py`. Hoje o upload e callback fixam schema 1; `/jobs/structured` e o payload antigo não protegem contra campos extras ignorados por workers antigos.  
**Dependências:** T04, T07. **TDD:** §§5.4–6, 8–9.

**Pronto quando:**

- [x] Dispatch V2 exige alvo explícito, modo e base coerentes em rota dedicada; o endpoint V1 preserva compatibilidade V1 e o worker novo rejeita alvo V2 explícito nesse endpoint. Não publicar capacidade V2 antes da T11.
- [x] O pipeline escolhe V1/V2 por alvo, carrega o snapshot correto, promove quando exigido, copia assets autorizados, usa renderer adequado e publica JSON/manifesto/HTML/JPEG imutáveis com schema e renderer efetivos. Ajustar o grafo: hoje `profile_overview` roda antes da escolha estruturada; edição V2 comum não pode buscar/analisar referências atuais antes de decidir se deve reaplicá-las. V1 conserva o caminho atual.
- [x] Callback repetido ou resposta incerta segue a política atual de idempotência e reconciliação; falhas de validação ou upload não publicam versão e não excluem artefatos cujo estado seja desconhecido. Emitir eventos categorizados de execução e quantidade de decorações sem prompts, imagens ou referências.

**Validação:** 28 testes de rotas, pipeline, persistência e referências com S3/LLM simulados passaram no Docker em 23/11/2026; Chromium foi validado na T04. A classificação de intenção de reaplicar referências usa LLM e rejeita respostas incertas.

**Verificar:** testes do payload, rotas, pipeline, upload e callback do worker, com S3/LLM simulados e Chromium quando necessário. **Commit:** `feat(worker): executar pipeline visual v2`.

### T09 — Schema alvo durável no job [P]

**Objetivo:** acrescentar ao job o schema alvo com migração aditiva e compatibilidade para jobs em voo.  
**Contexto:** `apps/api/internal/db/models.go`, migrations SQL existentes até `018`, repositórios de jobs e testes de migração. O alvo ainda não existe; `expected_version_id` já registra a base.  
**Dependências:** T02 para fixar o contrato e valores. **TDD:** §§4, 6–7, 9.

**Pronto quando:**

- [x] Migração aditiva e modelo suportam alvo V1/V2. O código novo registra alvo V1 nos jobs estruturados existentes; alvo V2 é exercitado em testes, mas sua seleção só chega na T12. Jobs estruturados anteriores ou criados por binários antigos sem alvo são interpretados como V1, inclusive em callback tardio. Jobs legados não exigem alvo estruturado.
- [x] Persistência do alvo participa da criação transacional do job; caminhos do código novo registram V1, enquanto inserções sem alvo de binários antigos continuam compatíveis. A seleção V2 fica na T12. Não altera snapshots, versões ou ponteiros existentes e não habilita V2 por si só.
- [x] Testes em PostgreSQL cobrem dados pré-migração, jobs antigos em voo, novos alvos e integridade/rollback não destrutivo da aplicação; não propor remover a migration enquanto houver dados V2.

**Validação:** suíte Go unitária completa e testes de migração/ciclo de vida em PostgreSQL descartável em 23/11/2026. O callback passa a comparar o alvo na T10.

**Verificar:** migrations e testes de repositório/integração com PostgreSQL. **Commit:** `feat(api): persistir schema alvo do job`.

### T10 — Publicação V2 e validação do callback

**Objetivo:** validar e publicar um callback de acordo com o schema alvo persistido e a base esperada.  
**Contexto:** `apps/api/internal/jobs/structured_complete.go`, `structured_document.go`, `apps/api/integration/structured_complete_test.go`, `structured_artifacts_test.go`. A API atual aceita somente schema 1 e retorna idempotentemente para jobs já concluídos.  
**Dependências:** T03, T09. **TDD:** §§4, 6–9.

**Pronto quando:**

- [x] Antes da primeira publicação, API exige schema do callback igual ao alvo do job, valida documento, renderer, correspondência entre IDs e manifesto, existência/prefixo dos objetos e vínculo job/chat; alvo ausente histórico significa V1. A autorização das fontes é verificada no dispatch e no worker; o manifesto sob o prefixo do job, isoladamente, não comprova a origem dos bytes. Se o desenho exigir comprovação independente no callback, persistir e validar autorização/proveniência do job como mudança explícita e compatível, não supor que ela já existe.
- [x] Concorrência, condição de base nula, nova raiz, callback repetido/resposta perdida e conflitos preservam a semântica atual. Repetição já concluída não cria versão adicional nem reprocessa artefatos.
- [x] Rejeições V2 não movem versão corrente nem removem objetos em resultado incerto; V1 e legado passam regressão. Os eventos terminais preservam idempotência e informam schema/renderer, resultado e motivo categorizado sem dados privados. Nenhum novo caminho de seleção V2 é ativado nesta tarefa.

**Validação:** suíte Go unitária e integração completa em PostgreSQL descartável, com casos adicionais V2 de alvo, idempotência e concorrência em 23/11/2026.

**Verificar:** unitários e integração Go/PostgreSQL de conclusão, artefatos e concorrência. **Commit:** `feat(api): publicar versões visuais v2`.

### T11 — Negociação de capacidades V2 e dispatch seguro

**Objetivo:** anunciar capacidades aditivas e garantir que jobs V2 usem apenas destinos e rota compatíveis.  
**Contexto:** `apps/worker/app/main.py`, `apps/api/internal/jobs/worker_client.go`, `worker_pool.go` e testes de capability. O contrato atual exige `structuredPost.contractVersion == 1`; preservar esse campo.  
**Dependências:** T08, T09. **TDD:** §§6–7, 9.

**Pronto quando:**

- [x] Workers novos anunciam leitura/escrita por versão e operações gráficas sem quebrar consumidores V1; campos ausentes significam somente V1. A API verifica todos os destinos diretos que poderão receber o job.
- [x] V2 usa exclusivamente a rota dedicada, mesmo que um worker antigo ignore campos extras; a rota valida alvo e não existe fallback para rota V1. Edição V1→V2 exige leitura V1/escrita V2; V2→V2 exige leitura/escrita V2.
- [x] Testes cobrem workers antigos/novos, ausência/erro/redirect, alteração após probe e resultado desconhecido; preservar semântica de rejeição explícita versus timeout/5xx no dispatch. Disponibilidade e incompatibilidade de capacidade são observáveis sem registrar respostas sensíveis.

**Validação:** testes do pacote Go `internal/jobs` e cinco testes de capacidades/rota do worker em Docker passaram em 23/11/2026.

**Verificar:** testes de pool, capability, endpoint e dispatch V1/V2. **Commit:** `feat: negociar capacidades visuais v2`.

### T12 — Seleção transacional do schema e flag

**Objetivo:** escolher e registrar o schema alvo por criação ou base de edição, com flag V2 desligada por padrão.  
**Contexto:** `apps/api/internal/config/`, `cmd/server/main.go`, `chat/service.go`, `chat/post_message.go`, repositórios e cliente de worker; `STRUCTURED_POSTS_ENABLED` atual controla apenas formato de novos chats.  
**Dependências:** T09, T10, T11. **TDD:** §§4, 6–7, 9.

**Pronto quando:**

- [x] Criação estruturada usa V1 com flag V2 desligada e V2 com flag ligada/capacidade; edição V1 é promovida com flag ligada e permanece V1 com flag desligada. Edição de base V2 continua V2 após desligar a flag e exige capacidade V2.
- [x] A base e o alvo são capturados atomicamente no aceite e despachados a um dos mesmos destinos diretos verificados; ausência de capacidade antes da mutação bloqueia o job, sem downgrade. Uma alteração de disponibilidade após o probe ainda pode falhar no dispatch e segue a semântica de resultado confirmado ou desconhecido. Nova criação explícita V1 após base V2 é nova raiz, não conversão, e continua sujeita a conflito.
- [x] A flag V2 não habilita novos chats estruturados por si; erros para o usuário não expõem conteúdo. É possível bloquear explicitamente mutações V2 em incidente, preservando leitura/download.

**Validação:** suíte unitária e integração Go, matriz transacional e dispatch HTTP em PostgreSQL descartável em 23/11/2026. Flags `STRUCTURED_VISUAL_V2_ENABLED` e `STRUCTURED_VISUAL_V2_MUTATIONS_DISABLED` têm padrão desligado.

**Verificar:** testes de configuração e integração HTTP/PostgreSQL para matriz da seção 7 do TDD e corridas de aceite/conclusão. **Commit:** `feat(api): controlar ativação visual v2`.

### T13 — Integração, compatibilidade e regressão ponta a ponta

**Objetivo:** comprovar o fluxo completo V1/V2 e legado com concorrência, referências e rollback.  
**Contexto:** `apps/api/integration/structured_*`, `hybrid_process_test.go`, `apps/worker/tests/test_structured_persistence.py`, `tests/e2e/test_hybrid.py`, `tests/docker_hybrid/`; reutilizar a infraestrutura isolada sem modificar dados de usuário.  
**Dependências:** T08, T10, T12. **TDD:** §§6–9.

**Pronto quando:**

- [x] Integração cobre criação V2, edição V1→V2 e V2→V2, edição textual sem referência original, aplicação explícita de referência indisponível e preservação de snapshots/assets/versões anteriores. Exercitar bloqueio de fontes de outro usuário no dispatch/worker e conferir manifesto, existência e prefixo no callback, sem confundir essas garantias com prova independente de proveniência dos bytes.
- [x] Duas edições concorrentes, primeira criação com base nula, nova raiz, callbacks fora de ordem/repetidos ou resposta perdida, falha parcial de upload e worker incompatível preservam atomicidade e limpeza segura.
- [x] E2E cobre histórico/download V1/V2/legado e rollback após V2 publicado, inclusive cliente existente e bloqueio seguro quando capacidade V2 faltar; não usa API antiga para confiar na proteção V2.

**Validação:** suites Go e worker, testes Chromium e ensaio Docker com LocalStack em 23/11/2026. Detalhes e serviços simulados em [validação](validacao.md).

**Verificar:** suítes Go/PostgreSQL, worker, testes entre processos e Docker; registrar quais serviços foram simulados. **Commit:** `test: cobrir compatibilidade visual v2`.

### T14 — Aceite visual e operação

**Objetivo:** executar o ensaio comparativo e registrar condições para ativação e rollback.  
**Contexto:** `tests/visual_reference_eval/`, `docs/avaliacoes/2026-11-23-referencias-visuais/`, `docs/RUNBOOK.md`, `docs/INTEGRATIONS.md` e T18 híbrida. A avaliação anterior teve somente duas amostras por condição e não comprova uma taxa de fidelidade.  
**Dependências:** T13; conclusão da T18 híbrida e decisões operacionais para ativação. **TDD:** §§7, 9–12.

**Pronto quando:**

- [ ] Fixture determinística para barra no topo verifica cor/posição resolvidas no HTML/JPEG; amostras com/sem referências incluem os dois exemplos anteriores, referências ambíguas, carrossel e marca real autorizada. Evidências distinguem o snapshot do resultado renderizado.
- [ ] Responsável revisa fidelidade, contraste e legibilidade; metas de custo, latência, falhas e qualidade são acordadas com base em medições, sem inferência estatística de amostra pequena. Implementar ou adaptar a agregação dos eventos categorizados de extração, validação, renderização, publicação e capacidade; verificar contagens, duração e ausência de conteúdo privado. Limitações, referência ausente e resultados são documentados.
- [ ] Runbook descreve flags, capacidade V1/V2, métricas, tratamento de órfãos e rollback seguro sem API antiga desprotegida; rollout/rollback e coleta são ensaiados no destino. Não habilitar tráfego antes da T18 e do aceite operacional.

**Verificar:** ensaio visual em Docker e ambiente controlado com S3 real, testes de observabilidade e revisão do responsável. **Commit:** `docs: registrar aceite visual v2`.

## Rastreabilidade por seção do TDD

| Seção | Tarefas |
| --- | --- |
| §4 — invariantes e preservação | T02, T05, T08–T13 |
| §5.1 — direção visual e cache | T01, T06, T07, T13–T14 |
| §5.2 — documento e promoção | T01–T05, T09–T10, T13 |
| §5.3 — edição | T01, T05, T07–T08, T12–T13 |
| §5.4 — renderer e contraste | T01, T04, T08, T13–T14 |
| §6 — fluxos e contratos | T07–T13 |
| §7 — compatibilidade e rollout | T09–T14 |
| §8 — segurança e privacidade | T02–T08, T10–T14 |
| §§9–12 — testes, operação e decisões | T01–T14 |
