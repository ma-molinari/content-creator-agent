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
| `API_UPSTREAM` | Web | Host e porta da API no proxy Nginx; Compose usa `api:8080` e a imagem usa por padrão `api.railway.internal:8080` |
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

Se alterar rotas ou handlers Go e a API correr dentro do Compose, reconstrua o serviço `api` antes de esperar novas URLs no navegador (ex.: `docker compose build api` e `docker compose up -d api`). Um binário antigo em `:8080` devolve **404** genérico ao frontend (via proxy Nginx no Compose ou Vite no desenvolvimento) quando a rota ainda não existia na build em execução — por exemplo `GET /chats/:id/contents/:contentId/download`.

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

O schema visual V2 tem controle separado: `STRUCTURED_VISUAL_V2_ENABLED=false` por
padrão. Não o habilite em tráfego antes da T18, do ensaio de fidelidade com marca
real e do aceite operacional. Com a flag ligada, novas criações estruturadas e
edições de bases V1 usam V2 quando todos os destinos anunciam as capacidades
necessárias. Desligá-la volta novas criações e edições V1 para V1, mas mantém
edições de bases V2 em V2; não converte versões existentes. A flag não cria chats
estruturados por si. Para bloquear todas as mutações V2 durante incidente, inclusive
edições de bases V2, use `STRUCTURED_VISUAL_V2_MUTATIONS_DISABLED=true`; leitura e
download continuam disponíveis.

Antes de qualquer escrita V2, atualize **todas** as réplicas da API que possam
receber callbacks e todos os workers elegíveis, aplique as migrations aditivas e
verifique leitura e escrita V2 em cada destino direto. A rota V2 é
`/jobs/structured/v2`; não a substitua pela rota V1. Para rollback, desabilite a
flag, drene os jobs e mantenha a API e os workers novos compatíveis com leitura e
edição V2. Não volte para uma API antiga que não valida o alvo do callback nem
remova migrations ou snapshots V2. Se houver jobs ou versões V2, a migration 019
recusa o rollback destrutivo.

Configure `STRUCTURED_WORKER_URLS` com uma lista separada por vírgulas, contendo um endereço direto e estável para cada réplica elegível; não use endereços balanceados nem redirecionamentos. A API consulta `/capabilities` em todos os destinos antes da mutação e distribui os jobs entre esses mesmos endereços usando `/jobs/structured`. Uma lista vazia ou uma réplica incompatível impede operações estruturadas; mudanças na disponibilidade após a verificação ainda podem causar falha no dispatch. Mantenha a lista atualizada e as réplicas compatíveis durante o rollout. `WORKER_URL` continua responsável pelo tráfego legado. Clientes compatíveis informam `X-Post-Client-Version: 1`. Para editar chats estruturados existentes após desligar a flag, a lista e os workers compatíveis devem permanecer disponíveis.

Referências visuais de perfil não são mais enviadas a novos jobs. As imagens já
copiadas para versões existentes permanecem nos respectivos snapshots. Veja o
procedimento de remoção dos arquivos de referência na seção abaixo.

Os eventos `[metrics] event=job_terminal` incluem IDs do job e chat, etapa, formato, resultado, código e duração em milissegundos; para versões estruturadas concluídas, incluem versões do schema e renderizador; callbacks idempotentes não geram uma segunda contagem. `[metrics] event=artifact_cleanup` informa o resultado e a quantidade tentada por lote, sem nomes de objetos. Tentativas repetidas podem contar novamente o mesmo objeto. Os eventos são logs, não uma série de métricas agregada: falhas confirmadas antes ou durante o dispatch também geram `job_terminal`; o watchdog gera um `job_terminal` por job encerrado, com formato e duração, além de `stuck_job_cleanup` com contagem agregada.

Para validar uma agregação local dos eventos sem exibir IDs ou conteúdo, a partir da raiz do repositório:

```powershell
docker compose logs --since 24h api | python tools/summarize_job_metrics.py
```

Para incluir os eventos V2 emitidos pelo worker na mesma agregação:

```powershell
docker compose logs --since 24h api worker | python tools/summarize_job_metrics.py
```

O campo `visual_v2` agrega extração, validação, renderização, publicação,
execução e disponibilidade de capacidade por resultado e motivo permitido, além
de p95 para eventos que informam duração e total de decorações reportadas. O
tempo de publicação mede o pipeline até o callback, não apenas o envio. Eventos
sem duração não entram no p95; cache, retentativas e múltiplas etapas podem gerar
mais de um evento por job. A ferramenta descarta campos fora da lista conhecida e
não agrega prompts, imagens, URLs, IDs ou textos. Ela não mede custo da LLM;
obtenha esse dado na telemetria autorizada do provedor e valide a coleta no destino.

O resumo conta resultados e calcula p95 de duração por formato, além de contar tentativas de limpeza e execuções do watchdog. Os eventos `artifact_reconcile` também informam inventários, jobs, prefixos, páginas, objetos listados, consultas de referência, chamadas de exclusão e duração por execução. `delete_calls` conta chamadas internas ao armazenamento, não necessariamente requisições faturadas pelo S3. O período deve ser delimitado na origem dos logs. A agregação depende da entrega dos logs e não deduplica entradas repetidas; objetos tentados novamente também são recontados. Ela não substitui a configuração e validação do coletor operacional nem define metas de rollout.


No fluxo estruturado, se a resposta do dispatch não chegar ou for 5xx, a API mantém o job em processamento: o worker pode tê-lo aceitado. O callback pode concluí-lo; caso não haja progresso ou conclusão, o watchdog o encerra conforme `STUCK_JOB_PROCESSING_MINUTES`. Uma rejeição explícita de dispatch só marca o job como falho se ele ainda não estiver terminal.

### Preparação e rollback

1. Antes de habilitar novos chats, confirme migrations, frontend compatível, todos os destinos diretos em `STRUCTURED_WORKER_URLS` e a disponibilidade das fontes; mantenha a reconciliação desligada até ensaiá-la em ambiente controlado com S3.
2. Estabeleça uma linha de base e combine metas de duração, falhas, conflitos, custo e qualidade visual antes de ampliar o tráfego. Valide o catálogo com uma marca real, pois as amostras aprovadas são genéricas.
3. Para interromper novas criações estruturadas, configure `STRUCTURED_POSTS_ENABLED=false` e aplique a configuração às réplicas da API. Preserve migrations, leitores e workers estruturados compatíveis e sua lista de destinos para continuar acessando e editando as versões existentes.
4. Em falhas repetidas de limpeza, mantenha `ARTIFACT_RECONCILE_ENABLED=false`, preserve os inventários e investigue permissões, disponibilidade do S3 e estado dos jobs antes de tentar novamente. Não remova objetos manualmente com base apenas em timeout.
# Retirada de referências visuais

O upload e o envio de referências de perfil a novos jobs foram desativados. A
remoção dos dados existentes é uma operação separada: atualize todas as instâncias
da API e pare instâncias antigas, aguarde os jobs ativos e execute, no ambiente
alvo com `DATABASE_URL` e credenciais S3 configurados:

```powershell
Set-Location apps/api
go run ./cmd/retire-references -apply
```

O comando recusa jobs pendentes ou em processamento, limita as exclusões aos
arquivos cadastrados no prefixo de referência do próprio usuário e apaga o objeto
antes da linha. Se interrompido, pode ser executado novamente. Assets copiados para
`slides/` não são removidos. A verificação de jobs não substitui parar as instâncias
antigas: elas poderiam iniciar um job usando referências durante a limpeza.

# Imagens do Openverse

A integração V3 é experimental e permanece desativada por padrão. Após validar
acesso ao Openverse e ao Wikimedia Commons, licenças e qualidade visual no ambiente
de destino, configure `STRUCTURED_POSTS_ENABLED=true`, `STRUCTURED_WORKER_URLS`
com os endereços diretos e `STRUCTURED_STOCK_IMAGES_ENABLED=true` na API. Todos
os workers selecionáveis devem anunciar leitura e escrita V3 e
`imageCompositionVersion: 2`. Para introduzir a composição focal em um ambiente
existente, suspenda o tráfego V3, drene os jobs e atualize todas as réplicas da
API e dos workers antes de retomá-lo: APIs antigas não aceitam o novo campo do
snapshot e workers antigos não conseguem editar snapshots que o contêm. A API
atual bloqueia workers sem essa capacidade antes de criar o job. Um rollback deve
manter leitores e workers compatíveis com os snapshots já criados; não há migração
de banco. A flag desligada impede novas raízes V3, mas uma versão V3 existente
continua exigindo worker V3 para edição, sem downgrade automático.

O fluxo permite adicionar ou trocar uma imagem de fundo por solicitação; pedidos
para várias imagens de uma vez devem ser divididos. A busca é anônima, restrita a
resultados CC0 do Wikimedia no Openverse e sujeita a disponibilidade e limites dos
serviços. Os créditos e a licença informada são preservados na versão e exibidos no
chat; o Openverse não garante a exatidão desses dados. O ensaio
`python tests/docker_hybrid/run_v3.py` usa LocalStack, Chromium, LLM e Openverse
simulados e não comprova disponibilidade ou licença no serviço real.

O worker registra `[metrics] event=stock_search` e `event=stock_selection` com
resultado, motivo e duração, sem termos de busca ou URLs. Para agregá-los junto
às métricas da API, execute da raiz do projeto:

```powershell
docker compose logs --since 24h api worker | python tools/summarize_job_metrics.py
```

O campo `stock` apresenta contagens por resultado e motivo e p95 de duração em
milissegundos para cada etapa. As contagens representam eventos, não usuários nem
jobs distintos: uma falha de busca também pode resultar em falha de seleção e logs
duplicados são recontados. Restringir o período na origem, monitorar volume de
amostras e garantir entrega dos logs no ambiente alvo. O acesso anônimo está sujeito
a limites e a busca não possui retentativa automática; defina metas e monitore
falhas e custos antes de ampliar o tráfego. Logs HTTPX e HTTPCore em INFO/DEBUG são
suprimidos no startup; logs anteriores podem conter consultas enviadas ao Openverse.
