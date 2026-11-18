# Geração híbrida — plano de tarefas

**Status:** em execução; T01 e T02 com implementação provisória e validação visual pendente.
**Requisitos:** `.specs/features/hybrid-post-generation/spec.md`
**Design e decisões:** `docs/TDD-MODELO-HIBRIDO.md`
**Instrução para execução por IA:** leia o TDD e os requisitos pertinentes, inspecione os arquivos e testes atuais antes de editar; não trate nomes de arquivos propostos como existentes. Cada tarefa entrega uma mudança coesa, testes adequados e um commit atômico em português. Não ativar o novo fluxo em produção até T18 e aprovação operacional. Arquivos/contratos compartilhados devem ser combinados antes de trabalho paralelo; `[P]` significa elegibilidade após dependências, não autorização para iniciar agentes.

## Dependências e integração

```text
T01 → T02 → T03 ───────────────────────────────────────┐
  ├→ T04 → T05 ────────────────────────────────────────┤
  ├→ T06 ──────────────────────────────────────────────┤
  └→ T07 → T12 ────────────────────────────────────────┤
T08 → T09 → T10 ───────────────────────────────────────┤
  └→ T11                                               │
T03 + T05 + T06 + T10 + T12 → T13 → T14               │
T10 → T15 → T17                                        │
T08 + T10 + T11 + T12 → T16                            │
T14 + T15 + T16 + T17 → T18                            ┘
```

T01 e T08 são trilhas iniciais independentes. Depois de T01, T02, T04, T06 e T07 podem avançar em paralelo; T09 e T11 podem avançar após T08. T10 depende apenas de T08 e T09; T13 integra os caminhos depois de T03, T05, T06, T10 e T12. T15 e T16 podem avançar após suas dependências. Coordene alterações em arquivos compartilhados: `[P]` indica elegibilidade técnica, não autorização para delegação. O diagrama expressa precedência, não estimativa de duração; um dos caminhos mais longos em número de tarefas é T01 → T02 → T03 → T13 → T14 → T18.

**Questões que precisam ser resolvidas durante o plano:** catálogo e limites V1 (T01), contratos de capacidade de clientes/workers (T10/T17), operação da reconciliação (T16) e métricas/limiares de rollout (T18). O TDD já determina que pedidos não representáveis falham com mensagem de reformulação; não implementar diálogo interativo nesta V1. Não inventar metas de negócio; registrar decisões e validação com o responsável quando necessárias.

## Tarefas

### T01 — Contrato do documento e catálogo inicial — implementação parcial

**Objetivo:** definir schema versionado e catálogo inicial de layouts, elementos, estilos e limites para snapshots estruturados.
**Contexto:** `apps/worker/app/state.py`, `slide_count_inference.py`, `config.py`; TDD, seção Contrato lógico. Novos módulos sob `apps/worker/app/`; schema deve diferenciar o pacote JSON atual que carrega HTML.
**Dependências:** nenhuma. **Requisitos:** HBG-01, HBG-02, HBG-10, HBG-12.
**Pronto quando:**
- [x] Documento valida tipos, IDs estáveis/únicos, single, limites de carrossel, layouts/estilos conhecidos e rejeita campos extras, URLs e HTML/CSS livre; escolhas do catálogo e limites ficam documentadas como propostas verificáveis.
- [x] Referências de imagem usam IDs, sem URL assinada; testes cobrem documentos válidos, inválidos e versão desconhecida.
- [ ] Validar catálogo e limites com o responsável antes de congelar o schema; até então são hipóteses do protótipo.
**Verificar:** executar testes pytest específicos do novo contrato no ambiente do worker. **Commit:** `feat(worker): definir contrato estruturado de posts`.

### T02 — Renderizador controlado de templates [P] — implementação parcial

**Objetivo:** transformar documentos válidos em HTML/CSS de slides usando templates versionados e escape de conteúdo.
**Contexto:** T01; `apps/worker/app/nodes/render_and_contrast.py`, `slide_design_checks.py`, `slide_render_html.py` e prompts existentes. Sem scripts do usuário ou recursos arbitrários; versionar renderizador e fontes.
**Dependências:** T01. **Requisitos:** HBG-01, HBG-02, HBG-10, HBG-12.
**Pronto quando:**
- [x] Templates suportam o catálogo inicial, assets por referência autorizada e saída de 1080×1350; texto é escapado e o HTML é determinístico.
- [ ] Completar testes de renderização visual, overflow e fontes indisponíveis; validar o catálogo com o responsável. Fontes Google e a incompatibilidade do validador legado com Inter exigem integração específica na T03.
**Verificar:** testes do renderizador e verificações de design do worker; capturas controladas para amostras. **Commit:** `feat(worker): renderizar documentos com templates controlados`.

### T03 — Captura e validação visual da saída estruturada — implementação parcial

**Objetivo:** integrar o HTML gerado às verificações de design, carregamento de assets, contraste e exportação JPEG existentes.
**Contexto:** `render_and_contrast.py`, `validate_design.py`, `slide_asset_wait.py`; não alterar silenciosamente o snapshot canônico na correção de contraste.
**Dependências:** T02. **Requisitos:** HBG-02, HBG-10, HBG-12.
**Pronto quando:**
- [x] Renderização isolada produz HTML derivado e JPEG 1080×1350; imagens ausentes, overflow identificável, fontes indisponíveis e falhas de renderização geram erro.
- [ ] Conectar a renderização ao grafo na T13 e testar regressão legada completa. Validações isoladas usam mocks e uma verificação manual no Chromium com fonte simulada.
**Verificar:** testes pytest específicos e Playwright Chromium do worker. **Commit:** `feat(worker): validar e exportar slides estruturados`.

### T04 — Operações tipadas de edição [P] — concluída no catálogo provisório

**Objetivo:** definir e aplicar atomicamente operações permitidas sobre uma cópia do snapshot.
**Contexto:** TDD, Fluxo de edição; `refinement_validate.py` demonstra limitações do legado. Começar por texto, fundo, estilo, imagem e layout dentro do catálogo T01.
**Dependências:** T01. **Requisitos:** HBG-03, HBG-10, HBG-12.
**Pronto quando:**
- [x] Operações validam alvos, propriedades e pré-condições; preservam IDs e número/ordem de slides, sem alterar campos fora do conjunto aplicado.
- [x] Sequência inválida não aplica parcialmente; testes incluem operação proibida, alvo ausente, base imutável e mudanças não pretendidas.
**Verificar:** pytest específico das operações e do schema. **Commit:** `feat(worker): aplicar edições estruturadas atômicas`.

### T05 — Planejamento de edição com LLM — integração inicial

**Objetivo:** gerar operações estruturadas a partir do pedido e da base autorizada, com retentativas limitadas e falha explícita.
**Contexto:** `generate_or_edit_slides.py`, `intent_detect.py`, `finalize_messages.py`; nova rota estruturada usa modo explícito, sem regex como autoridade. Preservar fluxo legado.
**Dependências:** T04. **Requisitos:** HBG-03, HBG-08, HBG-12.
**Pronto quando:**
- [ ] Respostas são validadas e falhas geram exceção segura de reformulação; status `failed`/`EDIT_UNSUPPORTED` está conectado; falta teste ponta a ponta na T14.
- [x] Testes isolados usam LLM simulada e verificam operações, erros e preservação da base; regressão de roteamento legado depende da T13.
**Verificar:** pytest dos novos nós e testes existentes de intenção/refinamento. **Commit:** `feat(worker): planejar edições por operações tipadas`.

### T06 — Geração estruturada com LLM [P] — concluída no catálogo provisório

**Objetivo:** gerar snapshot inicial válido a partir de plano, perfil e referências autorizadas.
**Contexto:** `generate_or_edit_slides.py`, `build_generation_plan.py`, `profile_overview.py`; não instruir LLM a gerar HTML. Quantidade inferida atualmente tem limite técnico 20, sem presumir que seja regra de produto aprovada.
**Dependências:** T01. **Requisitos:** HBG-01, HBG-02, HBG-10, HBG-12.
**Pronto quando:**
- [x] Fluxo converte resposta LLM em documento validado e aplica orçamento finito de retentativas com feedback seguro; erro terminal não gera saída parcial.
- [x] Testes simulam LLM, single/carrossel, formato inválido e ID de asset não autorizado.
**Verificar:** pytest específico do gerador e contrato. **Commit:** `feat(worker): gerar documentos estruturados com llm`.

### T07 — Assets imutáveis para cada versão — implementação parcial

**Objetivo:** resolver IDs autorizados e copiar assets utilizados para o prefixo do job, com manifesto de referências duráveis.
**Contexto:** `s3_image_utils.py`, `nodes/upload_assets.py`, `attachment_analyze.py`, `apps/api/internal/profile/service.go` e `jobs/worker_client.go`; o dispatch atual fornece chaves de referências do perfil, não seus IDs. Estender o contrato para fornecer mapeamento ID→chave autorizado para anexos, referências de perfil e assets herdados da base. Cópias incluem recursos herdados e não dependem do perfil permanecer inalterado.
**Dependências:** T01. **Requisitos:** HBG-07, HBG-10, HBG-12.
**Pronto quando:**
- [ ] Worker copia assets e grava `assets.json`; API envia referências próprias e anexos do chat e valida chaves herdadas restritas ao job da versão autorizada. Falta integrar o manifesto ao grafo e à reconciliação.
- [ ] Testes isolados cobrem cópia, manifesto, chaves de outro job e falha parcial; teste Postgres verifica isolamento das referências do perfil. Faltam testes integrados de persistência/releitura e ownership dos assets herdados.
**Verificar:** pytest dos serviços de assets e upload. **Commit:** `feat(worker): preservar assets por versão`.

### T08 — Migração e modelos de versionamento [P] — concluída

**Objetivo:** adicionar formato imutável do chat, ponteiro corrente, metadados de job e tabela de versões sem migrar conteúdo legado.
**Contexto:** `apps/api/internal/db/models.go`, migrations atuais até 016; verificar sequência novamente na execução. Usar referências consistentes por chat e tratar ciclo de FKs/exclusão.
**Dependências:** nenhuma. **Requisitos:** HBG-04, HBG-05, HBG-06, HBG-08, HBG-12.
**Pronto quando:**
- [x] Migração aditiva e modelos preservam dados existentes como `legacy_html`; novas versões impõem unicidade por job/mensagem e linhagem do mesmo chat.
- [x] Testes de migração com Postgres validam dados legados, constraints e exclusão; down migration não é usada em rollback com dados estruturados.
**Verificar:** testes de migração/modelos com Postgres e testes Go pertinentes. **Commit:** `feat(api): adicionar persistência de versões de posts`.

### T09 — Repositório de versões e seleção da base — concluída

**Objetivo:** disponibilizar operações de leitura e bloqueio de versão corrente/linhagem com ownership e formato.
**Contexto:** `apps/api/internal/chat/repository.go`, `jobs/repository.go`, `db/models.go`; evitar ordenação temporal como fonte da versão corrente.
**Dependências:** T08. **Requisitos:** HBG-04, HBG-05, HBG-10, HBG-12.
**Pronto quando:**
- [x] Leituras retornam versão corrente e histórico associados ao chat; seleção de base inválida ou de outro usuário/chat é rejeitada.
- [x] Testes Postgres exercitam ponteiro nulo, relações cruzadas e exclusão mútua no lock do chat; a ordem de locks de chat/job será aplicada na T10.
**Verificar:** testes de repositório e integração Postgres. **Commit:** `feat(api): consultar versões e bases de edição`.

### T10 — Aceite e conclusão transacional de jobs estruturados — implementação parcial

**Objetivo:** estender contratos HTTP e callback para persistir snapshots e publicar versões com controle de concorrência.
**Contexto:** `chat/handler.go`, `chat/post_message.go`, `jobs/worker_client.go`, `jobs/handler.go`, `jobs/complete.go`; tratamento atual do callback deve ser ajustado para não converter conflito em falha genérica. Implementar validação nos formatos JSON e multipart.
**Dependências:** T08, T09. **Requisitos:** HBG-04, HBG-05, HBG-06, HBG-08, HBG-10, HBG-12.
**Pronto quando:**
- [ ] `mode`/`baseVersionId` são validados por formato e ownership; job captura ponteiro esperado inclusive nulo; API recusa dispatch estruturado por padrão até que um verificador de capacidade confiável esteja disponível (T17); clientes não compatíveis não sofrem mutação. Verificador integrado e dispatch bem-sucedido testado; falta assegurar disponibilidade de todas as réplicas em ambientes mistos (T17).
- [ ] Callback valida prefixos, nomes, existência e quantidade de artefatos e, com locks consistentes, publica ou persiste `failed`/`VERSION_CONFLICT` atomicamente; repetições são idempotentes. Snapshot e manifesto têm leitura limitada e validação do contrato provisório, com exemplos compartilhados entre Go e Python; faltam mais casos de concorrência na T14.
**Verificar:** testes Go e integração Postgres para callbacks concorrentes, primeira criação nula, JSON/multipart, cliente legado e ownership. **Commit:** `feat(api): publicar versões estruturadas com controle de conflito`.

### T11 — Limpeza durável de chats e evicção [P] — implementação parcial

**Objetivo:** registrar inventário de artefatos antes da exclusão em cascata para limpeza idempotente de chats excluídos ou removidos pelo limite.
**Contexto:** `chat/repository.go` e `chat/service.go`: evicção atual remove o chat antes de coletar chaves; incluir anexos, imagens, HTMLs, snapshots, pacotes e assets. Tarefa durável não deve depender do chat excluído.
**Dependências:** T08. **Requisitos:** HBG-07, HBG-10, HBG-12.
**Pronto quando:**
- [ ] Exclusão/evicção registram inventário e IDs de jobs antes da cascata e tentam excluir chaves conhecidas; falta consumidor durável e verificação de referências/objetos adicionais na T16.
- [ ] Teste Postgres cobre sexto chat, cascata e falha S3; faltam repetição e integridade de objetos referenciados na reconciliação.
**Verificar:** testes de chat e integração Postgres/S3 simulado. **Commit:** `fix(api): preservar inventário de objetos na exclusão de chats`.

### T12 — Publicação de snapshot e artefatos no worker — implementação parcial

**Objetivo:** enviar documento, HTML, JPEG e manifesto imutável ao S3 e formar callback estruturado.
**Contexto:** `nodes/upload_assets.py`, `nodes/finalize.py`, `slide_artifact_cleanup.py`; uploads não são transação com o banco. Manter prefixo `slides/{jobId}/`.
**Dependências:** T01, T07. **Requisitos:** HBG-06, HBG-07, HBG-10, HBG-12.
**Pronto quando:**
- [ ] Snapshot, assets e artefatos são enviados com escrita condicional; falta inventário durável ou descoberta segura por prefixo (T16) e integração ao grafo.
- [ ] Helper envia o mesmo callback em retentativas sem fallback de erro; testes isolados cobrem timeout. Faltam integração e testes de resposta perdida após commit e conflito confirmado (T13/T14).
**Verificar:** pytest de upload/finalização com S3 e API simulados. **Commit:** `feat(worker): publicar artefatos de versões estruturadas`.

### T13 — Integrar caminho estruturado ao grafo — implementação parcial

**Objetivo:** conectar criação e edição estruturadas à validação, renderização, upload e progresso sem alterar o caminho legado.
**Contexto:** `graph.py`, `job_payload.py`, `state.py`, `main.py`; dispatch é HTTP com `BackgroundTasks`, não fila durável.
**Dependências:** T03, T05, T06, T10, T12. **Requisitos:** HBG-02, HBG-03, HBG-06, HBG-08, HBG-12.
**Pronto quando:**
- [ ] Grafo roteia por formato/modo explícitos e testes isolados cobrem status/erros; falta integração ponta a ponta com API, manifesto e reconciliação antes da ativação.
- [ ] Testes isolados com dependências simuladas cobrem criação, edição, erro, contrato e callback incerto; falta teste integrado com S3 simulado persistente e API.
**Verificar:** pytest do grafo e testes legados relevantes. **Commit:** `feat(worker): integrar geração híbrida ao grafo`.

### T14 — Cenários integrados de criação e concorrência

**Objetivo:** provar os contratos de ponta a ponta entre API, worker e persistência sob sucesso e falha.
**Contexto:** `apps/api/integration/`, `apps/worker/tests/`, `tests/e2e/`; usar Postgres real onde locking importa e serviços externos simulados sempre que possível.
**Dependências:** T13. **Requisitos:** HBG-02 a HBG-08, HBG-10, HBG-12.
**Pronto quando:**
- [ ] Postgres cobre criação/edição, duas primeiras criações com base nula e callbacks de edições fora de ordem/repetidos; faltam criar vs editar, timeout após commit e preservação semântica integrada ao worker.
- [ ] Cenários de uploads incompletos, troca de propriedade de assets e regressão legada não publicam versão indevida.
**Verificar:** suíte de integração Go/Postgres e testes de integração do worker; documentar dependências externas indisponíveis. **Commit:** `test: cobrir criação e concorrência de versões`.

### T15 — API de histórico e interface de modo/base [P] — implementação parcial

**Objetivo:** expor versão/formato no chat e permitir que o usuário envie criação ou edição da versão atual.
**Contexto:** `apps/api/internal/chat/handler.go`, `apps/web/src/api/chats.ts`, `pages/Chat.tsx`, `components/chat/` e `composer/`; preservar histórico e ZIP por resposta.
**Dependências:** T10. **Requisitos:** HBG-04, HBG-08, HBG-09, HBG-12.
**Pronto quando:**
- [x] Leitura inclui formato e versionId; frontend envia modo/base em JSON e multipart, apresenta a versão corrente e exige ação para reenviar após conflito.
- [ ] Testes de API e frontend cobrem versão atual, payload legado e conflito simulado. Rejeição de cliente antigo coberta; faltam validação ponta a ponta e negociação completa na T17.
**Verificar:** testes web e Go relevantes, build web e fluxo com API simulada. **Commit:** `feat(web): editar a versão atual do post`.

### T16 — Reconciliação segura de objetos órfãos [P] — implementação parcial

**Objetivo:** identificar e remover objetos não referenciados após estado terminal seguro, com inventário durável e coordenação com callback/upload.
**Contexto:** `internal/cron/`, `jobs/stuck.go`, `storage/s3.go` e limpeza do worker; não excluir após timeout de callback sem verificar estado. Definir mecanismo operacional antes de ativar.
**Dependências:** T08, T10, T11, T12. **Requisitos:** HBG-06, HBG-07, HBG-11, HBG-12.
**Pronto quando:**
- [ ] Reconciliação implementa varredura de inventários e jobs falhos com verificação de estado, referências e janela mínima de 24h; agendamento desativado por padrão. Faltam paginação, gestão de retenção dos inventários e validação operacional antes de habilitar.
- [ ] Teste Postgres cobre jobs ativos/falhos, objetos recentes/referenciados, repetição e falha temporária; faltam testes de callback incerto e recuperação real de processo.
**Verificar:** testes de integração de jobs/armazenamento com tempo e S3 controlados. **Commit:** `feat(api): reconciliar artefatos órfãos com segurança`.

### T17 — Capacidade, flag e observabilidade [P] — implementação parcial

**Objetivo:** controlar habilitação do formato e detectar incompatibilidade de clientes/replicas, registrando métricas e erros operacionais.
**Contexto:** `apps/api/internal/config/config.go`, `cmd/server/main.go`, `apps/worker/app/main.py`, `job_progress.py`; `/health` atual não negocia capacidade. Métricas de reconciliação são concluídas em T16; não depender de T16 para instrumentação básica.
**Dependências:** T10, T15. **Requisitos:** HBG-08, HBG-10, HBG-11, HBG-12.
**Pronto quando:**
- [ ] Flag desligada por padrão, negociação de cliente e verificação de capacidade implementadas; endpoint estruturado dedicado impede fallback legado em réplicas antigas. Falta assegurar disponibilidade de todos os destinos antes da mutação em ambientes com balanceamento misto.
- [ ] Métricas de formato, falhas, duração, conflitos e limpeza usam IDs/códigos sem conteúdo sensível; configuração e comportamento são testados.
**Verificar:** testes de configuração, negociação, logs e regressão com flag desligada. **Commit:** `feat: controlar ativação do fluxo híbrido`.

### T18 — Aceitação operacional e documentação

**Objetivo:** validar rollout/rollback e documentar operação, compatibilidade e limitações antes de habilitar tráfego.
**Contexto:** `docs/RUNBOOK.md`, `docs/ARCHITECTURE.md`, `docs/INTEGRATIONS.md`, `AGENTS.md`, TDD e suites de teste; preservar leitores e worker compatíveis ao desligar novas criações.
**Dependências:** T14, T15, T16, T17. **Requisitos:** HBG-01 a HBG-12.
**Pronto quando:**
- [ ] Execução registra evidências de criação/edição, versões legadas, corrida, timeout, limpeza, segurança e rollback; limitações/checagens não executadas ficam explícitas.
- [ ] Runbook descreve habilitação, capacidade, métricas, tratamento de órfãos, rollback não destrutivo e critérios de ativação; validação visual com exemplos reais e metas são acordadas com o responsável.
**Verificar:** suítes relevantes, ensaio de rollback com dados estruturados e revisão do responsável. **Commit:** `docs: registrar operação do fluxo híbrido`.

## Rastreabilidade

| Requisito | Tarefas |
| --- | --- |
| HBG-01 | T01, T02, T06, T18 |
| HBG-02 | T01, T02, T03, T06, T13, T14, T18 |
| HBG-03 | T04, T05, T13, T14, T18 |
| HBG-04 | T08, T09, T10, T14, T15, T18 |
| HBG-05 | T08, T09, T10, T14, T18 |
| HBG-06 | T08, T10, T12, T13, T14, T16, T18 |
| HBG-07 | T07, T11, T12, T14, T16, T18 |
| HBG-08 | T05, T08, T10, T13, T14, T15, T17, T18 |
| HBG-09 | T15, T18 |
| HBG-10 | T01–T04, T06–T12, T14, T17, T18 |
| HBG-11 | T16, T17, T18 |
| HBG-12 | T01–T18 |
