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
| `OPENAI_API_KEY` | API | Opcional; se definido, habilita cron de sumarização |
| `SUMMARIZE_CRON` | API | Cron em UTC (padrão `0 2 * * *`) |
| `STUCK_JOB_CRON` | API | Opcional; cron UTC para marcar jobs em `processing` há muito tempo como falha (padrão `*/10 * * * *`). Vazio desativa. |
| `STUCK_JOB_PROCESSING_MINUTES` | API | Idade mínima de `jobs.updated_at` em `processing` para falhar (padrão `20`). Valores baixos podem falhar jobs legítimos lentos. |

**Segurança operacional:** não escrever `WORKER_API_KEY` nem outros segredos em logs ou tickets. Rotacionar `WORKER_API_KEY` após suspeita de fuga. Endpoints `POST /internal/*` devem ficar apenas em rede privada (VPN, mesh interno, security group), não expostos à internet pública. Objetos de slides no S3 usam sempre chaves `slides/{job_id}/…` (UUID do job); o callback do worker só aceita chaves com esse prefixo.

Veja também `apps/api/.env.example` e `apps/worker/.env.example`.

## Deploy com Docker Compose (produção)

Subir stack com overrides de produção:

```bash
make prod-up
```

Encerrar:

```bash
make prod-down
```

O ficheiro `docker-compose.prod.yml` define `restart: unless-stopped` e injeta `COOKIE_SECURE`, `OPENAI_API_KEY` e `SUMMARIZE_CRON`. O texto de perfil (auditoria e marca) fica na base de dados via `PUT /profile` na aplicação.

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

## CI / segredos no GitHub

Para o job opcional de E2E contra Compose (`.github/workflows/ci.yml`), configure no repositório:

- `JWT_SECRET`, `JWT_REFRESH_SECRET`, `WORKER_API_KEY` (se aplicável ao teste)
- `OPENAI_API_KEY`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET`

O workflow principal executa testes unitários Go, integração com Postgres de serviço e Playwright no frontend.
