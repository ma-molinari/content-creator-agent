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

### T01 — Contrato do documento e catálogo inicial — concluída

**Objetivo:** definir schema versionado e catálogo inicial de layouts, elementos, estilos e limites para snapshots estruturados.
**Contexto:** `apps/worker/app/state.py`, `slide_count_inference.py`, `config.py`; TDD, seção Contrato lógico. Novos módulos sob `apps/worker/app/`; schema deve diferenciar o pacote JSON atual que carrega HTML.
**Dependências:** nenhuma. **Requisitos:** HBG-01, HBG-02, HBG-10, HBG-12.
**Pronto quando:**
- [x] Documento valida tipos, IDs estáveis/únicos, single, limites de carrossel, layouts/estilos conhecidos e rejeita campos extras, URLs e HTML/CSS livre; escolhas do catálogo e limites ficam documentadas.
- [x] Referências de imagem usam IDs, sem URL assinada; testes cobrem documentos válidos, inválidos e versão desconhecida.
- [x] Responsável aprovou o catálogo inicial V1 em 2026-11-18 após avaliar as amostras; o teto de 20 slides permanece técnico, sem se tornar regra de produto.
**Verificar:** executar testes pytest específicos do novo contrato no ambiente do worker. **Commit:** `feat(worker): definir contrato estruturado de posts`.

### T02 — Renderizador controlado de templates [P] — concluída

**Objetivo:** transformar documentos válidos em HTML/CSS de slides usando templates versionados e escape de conteúdo.
**Contexto:** T01; `apps/worker/app/nodes/render_and_contrast.py`, `slide_design_checks.py`, `slide_render_html.py` e prompts existentes. Sem scripts do usuário ou recursos arbitrários; versionar renderizador e fontes.
**Dependências:** T01. **Requisitos:** HBG-01, HBG-02, HBG-10, HBG-12.
**Pronto quando:**
- [x] Templates suportam o catálogo inicial, assets por referência autorizada e saída de 1080×1350; texto é escapado e o HTML é determinístico.
- [x] Testes cobrem overflow e fontes indisponíveis; amostras com fontes reais foram aprovadas pelo responsável. O caminho estruturado integra as verificações específicas na T03.
**Verificar:** testes do renderizador e verificações de design do worker; capturas controladas para amostras. **Commit:** `feat(worker): renderizar documentos com templates controlados`.

### T03 — Captura e validação visual da saída estruturada — concluída

**Objetivo:** integrar o HTML gerado às verificações de design, carregamento de assets, contraste e exportação JPEG existentes.
**Contexto:** `render_and_contrast.py`, `validate_design.py`, `slide_asset_wait.py`; não alterar silenciosamente o snapshot canônico na correção de contraste.
**Dependências:** T02. **Requisitos:** HBG-02, HBG-10, HBG-12.
**Pronto quando:**
- [x] Renderização isolada produz HTML derivado e JPEG 1080×1350; imagens ausentes, overflow identificável, fontes indisponíveis e falhas de renderização geram erro.
- [x] Renderização conectada ao grafo; testes automatizados cobrem imagem, overflow e fonte indisponível, com Chromium real no fluxo integrado. Amostras com fontes reais foram aprovadas; a suíte legada passou.
**Verificar:** testes pytest específicos e Playwright Chromium do worker. **Commit:** `feat(worker): validar e exportar slides estruturados`.

### T04 — Operações tipadas de edição [P] — concluída no catálogo V1

**Objetivo:** definir e aplicar atomicamente operações permitidas sobre uma cópia do snapshot.
**Contexto:** TDD, Fluxo de edição; `refinement_validate.py` demonstra limitações do legado. Começar por texto, fundo, estilo, imagem e layout dentro do catálogo T01.
**Dependências:** T01. **Requisitos:** HBG-03, HBG-10, HBG-12.
**Pronto quando:**
- [x] Operações validam alvos, propriedades e pré-condições; preservam IDs e número/ordem de slides, sem alterar campos fora do conjunto aplicado.
- [x] Sequência inválida não aplica parcialmente; testes incluem operação proibida, alvo ausente, base imutável e mudanças não pretendidas.
**Verificar:** pytest específico das operações e do schema. **Commit:** `feat(worker): aplicar edições estruturadas atômicas`.

### T05 — Planejamento de edição com LLM — concluída

**Objetivo:** gerar operações estruturadas a partir do pedido e da base autorizada, com retentativas limitadas e falha explícita.
**Contexto:** `generate_or_edit_slides.py`, `intent_detect.py`, `finalize_messages.py`; nova rota estruturada usa modo explícito, sem regex como autoridade. Preservar fluxo legado.
**Dependências:** T04. **Requisitos:** HBG-03, HBG-08, HBG-12.
**Pronto quando:**
- [x] Respostas são validadas e falhas geram exceção segura de reformulação; teste HTTP entre API e worker com LLM simulada verifica `failed`/`EDIT_UNSUPPORTED` sem publicar versão.
- [x] Testes isolados usam LLM simulada e verificam operações, erros e preservação da base; regressão de roteamento legado coberta na T13.
**Verificar:** pytest dos novos nós e testes existentes de intenção/refinamento. **Commit:** `feat(worker): planejar edições por operações tipadas`.

### T06 — Geração estruturada com LLM [P] — concluída no catálogo V1

**Objetivo:** gerar snapshot inicial válido a partir de plano, perfil e referências autorizadas.
**Contexto:** `generate_or_edit_slides.py`, `build_generation_plan.py`, `profile_overview.py`; não instruir LLM a gerar HTML. Quantidade inferida atualmente tem limite técnico 20, sem presumir que seja regra de produto aprovada.
**Dependências:** T01. **Requisitos:** HBG-01, HBG-02, HBG-10, HBG-12.
**Pronto quando:**
- [x] Fluxo converte resposta LLM em documento validado e aplica orçamento finito de retentativas com feedback seguro; erro terminal não gera saída parcial.
- [x] Testes simulam LLM, single/carrossel, formato inválido e ID de asset não autorizado.
**Verificar:** pytest específico do gerador e contrato. **Commit:** `feat(worker): gerar documentos estruturados com llm`.

### T07 — Assets imutáveis para cada versão — concluída

**Objetivo:** resolver IDs autorizados e copiar assets utilizados para o prefixo do job, com manifesto de referências duráveis.
**Contexto:** `s3_image_utils.py`, `nodes/upload_assets.py`, `attachment_analyze.py`, `apps/api/internal/profile/service.go` e `jobs/worker_client.go`; o dispatch atual fornece chaves de referências do perfil, não seus IDs. Estender o contrato para fornecer mapeamento ID→chave autorizado para anexos, referências de perfil e assets herdados da base. Cópias incluem recursos herdados e não dependem do perfil permanecer inalterado.
**Dependências:** T01. **Requisitos:** HBG-07, HBG-10, HBG-12.
**Pronto quando:**
- [x] Worker copia assets e grava `assets.json`; API envia referências próprias e anexos do chat e valida chaves herdadas restritas ao job da versão autorizada. O fluxo entre serviços preserva assets após remoção da referência original; operação da reconciliação permanece na T16.
- [x] Testes cobrem cópia, manifesto, chaves de outro job e falha parcial; Postgres verifica isolamento de referências e fluxo HTTP entre serviços verifica persistência e releitura em S3 simulado.
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

### T10 — Aceite e conclusão transacional de jobs estruturados — concluída no catálogo V1

**Objetivo:** estender contratos HTTP e callback para persistir snapshots e publicar versões com controle de concorrência.
**Contexto:** `chat/handler.go`, `chat/post_message.go`, `jobs/worker_client.go`, `jobs/handler.go`, `jobs/complete.go`; tratamento atual do callback deve ser ajustado para não converter conflito em falha genérica. Implementar validação nos formatos JSON e multipart.
**Dependências:** T08, T09. **Requisitos:** HBG-04, HBG-05, HBG-06, HBG-08, HBG-10, HBG-12.
**Pronto quando:**
- [x] `mode`/`baseVersionId` são validados por formato e ownership; job captura ponteiro esperado inclusive nulo; API recusa dispatch estruturado por padrão até que um verificador de capacidade confiável esteja disponível (T17); clientes não compatíveis não sofrem mutação. Verificador integrado e dispatch bem-sucedido testado; lista explícita de réplicas verificadas implementada (T17); o operador deve manter endereços diretos atualizados.
- [x] Callback valida prefixos, nomes, existência e quantidade de artefatos e, com locks consistentes, publica ou persiste `failed`/`VERSION_CONFLICT` atomicamente; repetições são idempotentes. Snapshot e manifesto têm leitura limitada e validação do contrato provisório, com exemplos compartilhados entre Go e Python; concorrência, callbacks repetidos e resposta perdida são cobertos na T14.
**Verificar:** testes Go e integração Postgres para callbacks concorrentes, primeira criação nula, JSON/multipart, cliente legado e ownership. **Commit:** `feat(api): publicar versões estruturadas com controle de conflito`.

### T11 — Limpeza durável de chats e evicção [P] — concluída

**Objetivo:** registrar inventário de artefatos antes da exclusão em cascata para limpeza idempotente de chats excluídos ou removidos pelo limite.
**Contexto:** `chat/repository.go` e `chat/service.go`: evicção atual remove o chat antes de coletar chaves; incluir anexos, imagens, HTMLs, snapshots, pacotes e assets. Tarefa durável não deve depender do chat excluído.
**Dependências:** T08. **Requisitos:** HBG-07, HBG-10, HBG-12.
**Pronto quando:**
- [x] Exclusão/evicção registram inventário e IDs de jobs antes da cascata; consumidor durável verifica referências e prefixos na T16. Falta validação operacional antes de habilitar a reconciliação.
- [x] Testes Postgres cobrem sexto chat, cascata, falha de armazenamento, repetição, proteção de referências e retomada em processo separado com armazenamento local.
**Verificar:** testes de chat e integração Postgres/S3 simulado. **Commit:** `fix(api): preservar inventário de objetos na exclusão de chats`.

### T12 — Publicação de snapshot e artefatos no worker — concluída no catálogo V1

**Objetivo:** enviar documento, HTML, JPEG e manifesto imutável ao S3 e formar callback estruturado.
**Contexto:** `nodes/upload_assets.py`, `nodes/finalize.py`, `slide_artifact_cleanup.py`; uploads não são transação com o banco. Manter prefixo `slides/{jobId}/`.
**Dependências:** T01, T07. **Requisitos:** HBG-06, HBG-07, HBG-10, HBG-12.
**Pronto quando:**
- [x] Snapshot, assets e artefatos usam escrita condicional, integração ao grafo e descoberta por prefixo; falta validação operacional da reconciliação (T16).
- [x] Helper envia o mesmo callback em retentativas sem fallback de erro; testes cobrem timeout, conflito confirmado e resposta perdida após commit entre processos.
**Verificar:** pytest de upload/finalização com S3 e API simulados. **Commit:** `feat(worker): publicar artefatos de versões estruturadas`.

### T13 — Integrar caminho estruturado ao grafo — concluída no catálogo V1

**Objetivo:** conectar criação e edição estruturadas à validação, renderização, upload e progresso sem alterar o caminho legado.
**Contexto:** `graph.py`, `job_payload.py`, `state.py`, `main.py`; dispatch é HTTP com `BackgroundTasks`, não fila durável.
**Dependências:** T03, T05, T06, T10, T12. **Requisitos:** HBG-02, HBG-03, HBG-06, HBG-08, HBG-12.
**Pronto quando:**
- [x] Grafo compilado roteia por formato/modo explícitos; testes com S3 simulado cobrem snapshots, manifesto e imagem herdada em criação/edição e verificam o roteamento legado. Teste local integra API HTTP, worker HTTP em segundo plano, Chromium e Postgres com armazenamento e LLM simulados; falta validação operacional da reconciliação antes da ativação.
- [x] Testes cobrem criação, edição, erro, contrato e callback incerto; S3 simulado persistente valida releitura e imutabilidade, com integração HTTP e renderização real.
**Verificar:** pytest do grafo e testes legados relevantes. **Commit:** `feat(worker): integrar geração híbrida ao grafo`.

### T14 — Cenários integrados de criação e concorrência — concluída em ambiente simulado

**Objetivo:** provar os contratos de ponta a ponta entre API, worker e persistência sob sucesso e falha.
**Contexto:** `apps/api/integration/`, `apps/worker/tests/`, `tests/e2e/`; usar Postgres real onde locking importa e serviços externos simulados sempre que possível.
**Dependências:** T13. **Requisitos:** HBG-02 a HBG-08, HBG-10, HBG-12.
**Pronto quando:**
- [x] Postgres cobre criação/edição, criação vs edição, duas primeiras criações com base nula e callbacks fora de ordem/repetidos; o worker testa resposta perdida após commit simulado. Postgres cobre callback concluído antes de erro de dispatch e dispatch de resultado desconhecido; ensaio entre processos derruba a conexão após o commit e confirma retentativa idempotente. O ensaio Docker usou S3 e LLM simulados; a infraestrutura real permanece como validação operacional na T18.
- [x] Postgres cobre snapshot/manifesto/imagem ausentes, documento inválido e asset de outro job sem publicação; HTTP verifica acesso de outro usuário e roteamento legado. A validação com S3 real permanece na T18.
**Verificar:** suíte de integração Go/Postgres e testes de integração do worker; documentar dependências externas indisponíveis. **Commit:** `test: cobrir criação e concorrência de versões`.

### T15 — API de histórico e interface de modo/base [P] — concluída no catálogo V1

**Objetivo:** expor versão/formato no chat e permitir que o usuário envie criação ou edição da versão atual.
**Contexto:** `apps/api/internal/chat/handler.go`, `apps/web/src/api/chats.ts`, `pages/Chat.tsx`, `components/chat/` e `composer/`; preservar histórico e ZIP por resposta.
**Dependências:** T10. **Requisitos:** HBG-04, HBG-08, HBG-09, HBG-12.
**Pronto quando:**
- [x] Leitura inclui formato e versionId; frontend envia modo/base em JSON e multipart, apresenta a versão corrente e exige ação para reenviar após conflito.
- [x] Testes de API e frontend cobrem versão atual, payload legado e conflito simulado; HTTP com Postgres cobre criação JSON, edição multipart e rejeição de cliente antigo. Teste local cobre API e worker HTTP com dependências externas simuladas; falta ensaio com infraestrutura real.
**Verificar:** testes web e Go relevantes, build web e fluxo com API simulada. **Commit:** `feat(web): editar a versão atual do post`.

### T16 — Reconciliação segura de objetos órfãos [P] — implementação parcial

**Objetivo:** identificar e remover objetos não referenciados após estado terminal seguro, com inventário durável e coordenação com callback/upload.
**Contexto:** `internal/cron/`, `jobs/stuck.go`, `storage/s3.go` e limpeza do worker; não excluir após timeout de callback sem verificar estado. Definir mecanismo operacional antes de ativar.
**Dependências:** T08, T10, T11, T12. **Requisitos:** HBG-06, HBG-07, HBG-11, HBG-12.
**Pronto quando:**
- [ ] Reconciliação implementa varredura de inventários e jobs falhos com verificação de estado, referências e janela mínima de 24h; agendamento desativado por padrão. Consultas de inventários e jobs e listagem S3 são paginadas; inventários são retidos indefinidamente até existir limite comprovado de duração do worker; falta validar custo e operação antes de habilitar.
- [x] Testes cobrem jobs ativos/falhos, objetos recentes/referenciados, repetição e callback com resposta perdida; recuperação após interrupção foi ensaiada em Docker com S3 simulado.
**Verificar:** testes de integração de jobs/armazenamento com tempo e S3 controlados. **Commit:** `feat(api): reconciliar artefatos órfãos com segurança`.

### T17 — Capacidade, flag e observabilidade [P] — concluída localmente

**Objetivo:** controlar habilitação do formato e detectar incompatibilidade de clientes/replicas, registrando métricas e erros operacionais.
**Contexto:** `apps/api/internal/config/config.go`, `cmd/server/main.go`, `apps/worker/app/main.py`, `job_progress.py`; `/health` atual não negocia capacidade. Métricas de reconciliação são concluídas em T16; não depender de T16 para instrumentação básica.
**Dependências:** T10, T15. **Requisitos:** HBG-08, HBG-10, HBG-11, HBG-12.
**Pronto quando:**
- [x] Flag desligada por padrão, negociação de cliente e verificação de todos os destinos estruturados configurados antes da mutação; dispatch usa os mesmos endereços diretos e endpoint dedicado. A operação exige lista completa e atualizada, sem balanceador.
- [x] Callbacks terminais e limpeza emitem eventos de formato, resultado, duração, conflito e quantidade sem conteúdo de posts; dispatch confirmado e watchdog geram evento terminal por formato; agregador validado com logs Docker; coleta e agregação reais permanecem na T18.
**Verificar:** testes de configuração, negociação, logs e regressão com flag desligada. **Commit:** `feat: controlar ativação do fluxo híbrido`.

### T18 — Aceitação operacional e documentação

**Objetivo:** validar rollout/rollback e documentar operação, compatibilidade e limitações antes de habilitar tráfego.
**Contexto:** `docs/RUNBOOK.md`, `docs/ARCHITECTURE.md`, `docs/INTEGRATIONS.md`, `AGENTS.md`, TDD e suites de teste; preservar leitores e worker compatíveis ao desligar novas criações.
**Dependências:** T14, T15, T16, T17. **Requisitos:** HBG-01 a HBG-12.
**Pronto quando:**
- [ ] Testes locais registram criação/edição, legado, isolamento entre usuários, corrida, resposta perdida, limpeza e rollback da flag; o ensaio Docker simulou S3 e LLM. Falta ensaio com serviços reais.
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
