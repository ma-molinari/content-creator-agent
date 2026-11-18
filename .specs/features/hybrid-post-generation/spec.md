# Geração híbrida de posts — requisitos

**Status:** rascunho para revisão. **Design:** `docs/TDD-MODELO-HIBRIDO.md`. O TDD é a referência de arquitetura; este índice identifica requisitos para rastrear as tarefas. Questões em aberto não são decisões aprovadas.

- **HBG-01 — Contrato:** documento canônico JSON versionado, com slides/elementos de IDs estáveis, limites, templates flexíveis e referências de assets autorizadas; HTML livre da LLM não é aceito no fluxo estruturado.
- **HBG-02 — Criação:** LLM gera documento validado, renderizador controlado produz HTML e Playwright gera JPEG; preservar setup, tipo de post, anexos e status assíncrono.
- **HBG-03 — Edição:** operações tipadas aplicadas atomicamente à versão corrente preservam campos não afetados; pedidos inválidos não aplicam alterações parciais.
- **HBG-04 — Versionamento:** snapshots imutáveis por job, versões explícitas e histórico; criação no mesmo chat inicia nova raiz; formatos e dados legados não são convertidos automaticamente.
- **HBG-05 — Concorrência:** aceite e conclusão verificam base; compare-and-set transacional da versão corrente inclusive quando nula; conflitos não substituem resultado já publicado.
- **HBG-06 — Persistência:** API valida artifacts e os registra com mensagem, slides, versão e job em transação idempotente; S3 e PostgreSQL não são transacionais entre si.
- **HBG-07 — Assets e limpeza:** versões mantêm cópias dos assets utilizados; exclusão, evicção e reconciliação são duráveis, idempotentes e seguras diante de callbacks incertos.
- **HBG-08 — Contratos e compatibilidade:** JSON e multipart com modo/base explícitos; chats legados permanecem legados; clientes/worker antigos não recebem trabalho estruturado sem proteção.
- **HBG-09 — UX:** interface identifica versão corrente, escolhe criação ou edição, apresenta conflitos e erros de reformulação e mantém histórico e downloads.
- **HBG-10 — Segurança:** ownership em todos os limites; schema restrito, escape, limites de recursos, rede controlada e logs sem informações sensíveis.
- **HBG-11 — Operação:** observabilidade, flag desligada por padrão, implantação compatível, reconciliação e rollback sem corromper versões estruturadas.
- **HBG-12 — Validação:** testes relevantes de schema, operação, renderização, API, Postgres concorrente, integração, compatibilidade, segurança e rollback.

**Decisões do usuário:** templates flexíveis; edição linear da versão mais recente com rejeição de conflito; responsável técnico é o usuário; sem ticket. **Fora do escopo:** editor visual, ramificações, conversão automática de legado e publicação no Instagram.
