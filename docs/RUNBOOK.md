# Runbook — Content Creator Agent

## Variáveis obrigatórias em produção

| Variável | Onde | Notas |
| -------- | ---- | ----- |
| `DATABASE_URL` | API | Postgres com SSL apropriado em produção |
| `JWT_SECRET`, `JWT_REFRESH_SECRET` | API | Strings longas e aleatórias |
| `WORKER_API_KEY` | API + Worker | Mesmo valor em ambos |
| `WORKER_URL` | API | Base URL do worker (ex.: `http://worker:8000`) |
| `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET` | API + Worker | Necessários para uploads e ZIP |
| `COOKIE_SECURE` | API | `true` em HTTPS (override de dev com `false`) |
| `OPENAI_API_KEY` | API | Opcional; se definido, habilita cron de sumarização |
| `SUMMARIZE_CRON` | API | Cron em UTC (padrão `0 2 * * *`) |

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
