# Runbook — Post Mind

## Variáveis obrigatórias em produção

| Variável | Onde | Notas |
| -------- | ---- | ----- |
| `DATABASE_URL` | API | Postgres com SSL apropriado em produção |
| `JWT_SECRET`, `JWT_REFRESH_SECRET` | API | Strings longas e aleatórias |
| `WORKER_API_KEY` | API + Worker | Mesmo valor em ambos |
| `WORKER_URL` | API | Base URL do worker (ex.: `http://worker:8000`) |
| `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET` | API + Worker | Necessários para uploads e ZIP |
| `COOKIE_SECURE` | API | `true` em HTTPS (override de dev com `false`); ver `docker-compose.prod.yml` |
| `OPENAI_API_KEY` | Worker | Obrigatória para geração no worker |
| `STUCK_JOB_CRON` | API | Opcional; cron UTC para marcar jobs em `processing` há muito tempo como falha (padrão `*/10 * * * *`). Ausente ou vazio usa o padrão. |
| `STUCK_JOB_PROCESSING_MINUTES` | API | Idade mínima do último heartbeat ou `jobs.updated_at` em `processing` para falhar (padrão `20`). Valores baixos podem falhar jobs legítimos lentos. |
| `ARTIFACT_RECONCILE_ENABLED` | API | Padrão `false`; manter desativado até validar a operação e os limites de reconciliação. |
| `ARTIFACT_RECONCILE_CRON`, `ARTIFACT_RECONCILE_GRACE_HOURS` | API | Padrões `0 4 * * *` UTC e 24 horas; limite mínimo de 24 horas. |

**Segurança operacional:** não escrever `WORKER_API_KEY` nem outros segredos em logs ou tickets. Rotacionar `WORKER_API_KEY` após suspeita de fuga. Endpoints `POST /internal/*` usam a porta interna `8081`; `GO_API_URL` do worker deve apontar para ela. Eles devem ficar apenas em rede privada (VPN, mesh interno, security group), não expostos à internet pública. Objetos de slides no S3 usam sempre chaves `slides/{job_id}/…` (UUID do job); o callback do worker só aceita chaves com esse prefixo.

A reconciliação mantém inventários permanentemente e percorre inventários, jobs falhos e objetos S3 em páginas; monitore crescimento e custo e não habilite até validar esses limites. A retenção indefinida impede perder o registro de uploads tardios, pois não há prazo máximo garantido de execução do worker. Não remova inventários por idade sem estabelecer e validar antes um limite seguro de duração e encerramento dos workers. Veja também `apps/api/.env.example` e `apps/worker/.env.example`.

## Deploy com Docker Compose (produção)

Subir stack com overrides de produção:

```bash
make prod-up
```

Encerrar:

```bash
make prod-down
```

O ficheiro `docker-compose.prod.yml` define `restart: unless-stopped` e injeta `COOKIE_SECURE`. O texto de perfil (auditoria e marca) fica na base de dados via `PUT /profile` na aplicação.

## Health checks

| Serviço | URL |
| ------- | --- |
| API | `GET http://<host>:8080/health` |
| Worker | `GET http://<host>:8000/health` |

## Desenvolvimento local (API em Docker)

Se alterar rotas ou handlers Go e a API correr dentro do Compose, reconstrua o serviço `api` antes de esperar novas URLs no navegador (ex.: `docker compose build api` e `docker compose up -d api`). Um binário antigo em `:8080` devolve **404** genérico ao frontend (via Vite proxy) quando a rota ainda não existia na build em execução — por exemplo `GET /chats/:id/contents/:contentId/download`.

## Logs por `job_id`

A API e o worker passam a registar `job_id` em pontos críticos.

Filtrar logs da API (exemplo):

```bash
docker compose logs api | grep "job_id=<uuid>"
```

No worker:

```bash
docker compose logs worker | grep "job_id=<uuid>"
```

## Migrations

Na máquina com `DATABASE_URL` configurado (ou `.env` na pasta `apps/api`):

```bash
cd apps/api && make migrate-up
```

## CI

Não há workflow de CI versionado neste repositório. Consulte `docs/TESTING.md` para executar os testes localmente e configure os segredos no provedor de CI escolhido quando houver pipeline.

## Geração estruturada (em desenvolvimento)

`STRUCTURED_POSTS_ENABLED` é `false` por padrão. Não habilite a flag em produção antes da validação e aceitação previstas na T18. Quando habilitada, novos chats de clientes compatíveis podem usar o formato estruturado; desabilitar a flag preserva a edição dos chats estruturados existentes.

Configure `STRUCTURED_WORKER_URLS` com uma lista separada por vírgulas, contendo um endereço direto e estável para cada réplica elegível; não use endereços balanceados nem redirecionamentos. A API consulta `/capabilities` em todos os destinos antes da mutação e distribui os jobs entre esses mesmos endereços usando `/jobs/structured`. Uma lista vazia ou uma réplica incompatível impede operações estruturadas; mudanças na disponibilidade após a verificação ainda podem causar falha no dispatch. Mantenha a lista atualizada e as réplicas compatíveis durante o rollout. `WORKER_URL` continua responsável pelo tráfego legado. Clientes compatíveis informam `X-Post-Client-Version: 1`. Para editar chats estruturados existentes após desligar a flag, a lista e os workers compatíveis devem permanecer disponíveis.

Os eventos `[metrics] event=job_terminal` incluem IDs do job e chat, etapa, formato, resultado, código e duração em milissegundos; para versões estruturadas concluídas, incluem versões do schema e renderizador; callbacks idempotentes não geram uma segunda contagem. `[metrics] event=artifact_cleanup` informa o resultado e a quantidade tentada por lote, sem nomes de objetos. Tentativas repetidas podem contar novamente o mesmo objeto. Os eventos são logs, não uma série de métricas agregada: falhas confirmadas antes ou durante o dispatch também geram `job_terminal`; o watchdog gera um `job_terminal` por job encerrado, com formato e duração, além de `stuck_job_cleanup` com contagem agregada.

Para validar uma agregação local dos eventos sem exibir IDs ou conteúdo, a partir da raiz do repositório:

```powershell
docker compose logs --since 24h api | python tools/summarize_job_metrics.py
```

O resumo conta resultados e calcula p95 de duração por formato, além de contar tentativas de limpeza e execuções do watchdog. Os eventos `artifact_reconcile` também informam inventários, jobs, prefixos, páginas, objetos listados, consultas de referência, chamadas de exclusão e duração por execução. `delete_calls` conta chamadas internas ao armazenamento, não necessariamente requisições faturadas pelo S3. O período deve ser delimitado na origem dos logs. A agregação depende da entrega dos logs e não deduplica entradas repetidas; objetos tentados novamente também são recontados. Ela não substitui a configuração e validação do coletor operacional nem define metas de rollout.


No fluxo estruturado, se a resposta do dispatch não chegar ou for 5xx, a API mantém o job em processamento: o worker pode tê-lo aceitado. O callback pode concluí-lo; caso não haja progresso ou conclusão, o watchdog o encerra conforme `STUCK_JOB_PROCESSING_MINUTES`. Uma rejeição explícita de dispatch só marca o job como falho se ele ainda não estiver terminal.

### Preparação e rollback

1. Antes de habilitar novos chats, confirme migrations, frontend compatível, todos os destinos diretos em `STRUCTURED_WORKER_URLS` e a disponibilidade das fontes; mantenha a reconciliação desligada até ensaiá-la em ambiente controlado com S3.
2. Estabeleça uma linha de base e combine metas de duração, falhas, conflitos, custo e qualidade visual antes de ampliar o tráfego. Valide o catálogo com uma marca real, pois as amostras aprovadas são genéricas.
3. Para interromper novas criações estruturadas, configure `STRUCTURED_POSTS_ENABLED=false` e aplique a configuração às réplicas da API. Preserve migrations, leitores e workers estruturados compatíveis e sua lista de destinos para continuar acessando e editando as versões existentes.
4. Em falhas repetidas de limpeza, mantenha `ARTIFACT_RECONCILE_ENABLED=false`, preserve os inventários e investigue permissões, disponibilidade do S3 e estado dos jobs antes de tentar novamente. Não remova objetos manualmente com base apenas em timeout.
