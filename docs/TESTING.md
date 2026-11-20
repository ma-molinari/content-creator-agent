# Testing Infrastructure

## Test Frameworks

| Layer | Framework | Location |
|-------|-----------|----------|
| Go unit | `testing` + `stretchr/testify` v1.11.1 | `apps/api/internal/**/*_test.go` |
| Go integration | `testing` + `testify` + `net/http/httptest` | `apps/api/integration/` |
| Python E2E | pytest + httpx | `tests/e2e/` |
| Web screenshots | Playwright (`@playwright/test`) | `apps/web/e2e/` |

## Test Organization

### Go Unit Tests

**Location:** co-located with production code, same package.
**Naming:** `<unit>_test.go`.
**Build tag:** none (run by default with `go test ./...`).

Files observed:
- `apps/api/internal/auth/service_test.go`
- `apps/api/internal/chat/service_test.go`
- `apps/api/internal/jobs/repository_test.go`
- `apps/api/internal/jobs/slide_key_test.go`
- `apps/api/internal/profile/service_test.go`
- `apps/api/internal/config/config_test.go`
- `apps/api/internal/db/db_test.go`
- `apps/api/internal/storage/s3_test.go`

**DB approach for repo/service tests:** SQLite in-memory via GORM driver (`gorm.io/driver/sqlite`). Allows running without a Postgres instance.

### Go Integration Tests

**Location:** `apps/api/integration/`
**Build tag:** `//go:build integration` — excluded from the default `go test ./...` run.
**Requirement:** `INTEGRATION_DATABASE_URL` env var (real Postgres). Tests are skipped when unset.

**What they test:**
- `auth_test.go` — register, login, refresh cookie, password recovery
- `chat_crud_test.go` — chat CRUD operations
- `dispatch_test.go` — full async job dispatch + worker callback cycle
- `failure_test.go` — worker error propagation, job status `failed`
- `profile_test.go` — profile save, reference upload/delete
- `security_test.go` — CORS headers, rate limiting

**Test environment setup (`helpers_test.go`):**
`newTestEnv(t, workerHandler)` wires:
1. Real Postgres via `INTEGRATION_DATABASE_URL` (migrations applied)
2. `httptest.NewServer` for the Echo API
3. `httptest.NewServer` for a mock worker (controllable per test)
4. `mockStorage{}` (no real S3; presigned URLs return `https://integration.test/presigned/<key>`)

The mock worker handler receives the dispatch, can call back the real API (`POST /internal/jobs/:id/complete`) to simulate success or failure, enabling end-to-end job lifecycle tests without real LLM or S3.

**Shared helpers:**
- `registerAndLogin(t, env)` → `(accessToken, userID)`
- `createChat(t, env, token)` → `chatID`
- `postMessage(t, env, token, chatID, content)` → `jobID`
- `getJobStatus(t, env, token, chatID, jobID)` → `(status, errMsg)`
- `pollJobDone(t, env, token, chatID, jobID, timeout)` → terminal status

### Python E2E Tests

**Location:** `tests/e2e/`
**Runner:** pytest
**Dependencies:** `httpx`, configured in `tests/e2e/requirements.txt`
**Target:** full Docker Compose stack (`docker compose up -d --build --wait`)

**What they test:**
`test_smoke.py::test_full_post_creation_flow` — exercises the complete user journey:
1. Register user
2. Configure profile (audit + brand text)
3. Create chat
4. Post message → receive `202 {jobId}`
5. Poll `GET /chats/:id/jobs/:jobId/status` (up to 120s) until `done`
6. Assert assistant message + at least one image artifact with an S3 key

This is the only test that calls real OpenAI and writes to real S3.

### Web Screenshot Tests

**Location:** `apps/web/e2e/`
**Framework:** `@playwright/test` v1.59.1
**Config:** `apps/web/playwright.config.ts`
**Command:** `npm run screenshots` (builds Vite first, then runs Playwright)
**Purpose:** capture screenshots of the UI for visual verification / design review (not assertions-based regression tests).

## Test Execution

### API unit tests

```bash
cd apps/api
make test
# equivalent: go test ./...
```

### API integration tests

```bash
export INTEGRATION_DATABASE_URL="postgres://app:app@localhost:5432/content_creator?sslmode=disable"
cd apps/api
make test-integration
# equivalent: go test -tags=integration -v ./integration/...
```

### Full E2E (Docker Compose + real LLM)

```bash
# From repo root — requires .env files with OPENAI_API_KEY, AWS_*, etc.
make e2e
# Runs: docker compose up -d --build --wait && pytest && docker compose down
```

### Web screenshots

```bash
cd apps/web
npm run screenshots
```

## Coverage Targets

**Current:** No coverage tooling or thresholds configured.
**Enforcement:** None automated. CI is not documented in the repository; tests are run manually or via `make e2e`.

## Notable Testing Patterns

- **Integration tests use a mock S3** (`mockStorage{}`). Real S3 is only exercised in full E2E.
- **Worker is mocked per-test** in integration tests via a controllable `httptest.Server`. The handler receives the dispatch and can immediately call back (or simulate delay/failure) without an LLM.
- **SQLite swap for unit tests** keeps unit tests fast and dependency-free (no Docker needed). Schema compatibility with PostgreSQL is tested at the integration layer.
- **E2E tests embed test data** (`testdata/AUDIT.md`, `testdata/BRAND.md`) via Go `//go:embed` to provide realistic profile content without filesystem coupling.

### Smoke test do renderizador estruturado

`apps/worker/tests/test_structured_browser.py` é opcional e exige Chromium instalado para a versão do Playwright utilizada e uma fonte TTF local. Execute no ambiente do worker com `RUN_CHROMIUM_TESTS=1` e `TEST_FONT_PATH` apontando para o arquivo. O teste intercepta a fonte externa, não acessa a rede e cobre imagem, overflow e ausência de fonte. Ele usa uma fonte de teste, portanto não substitui a validação visual das fontes e layouts reais.

### Integração local Go + Python sem Docker

Com PostgreSQL disponível em `INTEGRATION_DATABASE_URL`, instale as dependências do worker e informe o caminho do interpretador em `HYBRID_E2E_PYTHON`. A partir de `apps/api`, execute:

```powershell
$env:HYBRID_E2E_PYTHON = "C:\caminho\para\worker\.venv\Scripts\python.exe"
go test -tags=integration ./integration -run "TestHybridGoAndPythonProcesses|TestHybridRealWorkerHTTP" -count=1
```

Os testes criam uma API HTTP local e executam o grafo Python em outro processo, incluindo um cenário com o endpoint HTTP real do worker e execução em segundo plano. Arquivos ficam em diretório temporário compartilhado; callbacks, versões e edição são verificados no PostgreSQL. LLM, renderização e S3 são simulados por padrão. Para usar o renderizador e Chromium reais, defina também `HYBRID_E2E_REAL_RENDER=1`; são necessários Chromium compatível e acesso às fontes dos templates. A LLM e o S3 continuam simulados. O cenário HTTP derruba a conexão após o commit do callback para verificar a retentativa idempotente. Os testes não substituem o E2E com infraestrutura real.

### E2E estruturado em ambiente não produtivo

O teste `tests/e2e/test_hybrid.py` é opt-in e exercita criação, edição, histórico e downloads com worker, LLM e S3 do ambiente informado. Ele cria uma conta de teste e exclui o chat criado ao final; a conta permanece cadastrada. Execute somente em um ambiente não produtivo dedicado, com a flag estruturada e os workers compatíveis configurados. A execução faz chamadas reais à LLM e ao S3.

```powershell
$env:E2E_API_URL = "http://localhost:8080"
$env:E2E_HYBRID = "1"
python -m pytest tests/e2e/test_hybrid.py -v
Remove-Item Env:E2E_HYBRID
```

Sem `E2E_HYBRID=1`, o teste é ignorado. O arquivo `test_hybrid_contract.py` valida o próprio teste com HTTP simulado e não acessa serviços externos.

### Ensaio Docker isolado sem bucket

O ensaio reproduzível usa containers temporários de API, worker, PostgreSQL e um simulador S3 HTTP. A API é compilada a partir do código atual; o worker usa o código atual montado no container. Geração e edição pela LLM são simuladas, e Chromium usa uma fonte de teste local. O simulador cobre apenas as operações necessárias ao ensaio e não implementa todo o protocolo S3.

A partir da raiz, com Docker, Go, Python e `httpx` instalados e as imagens `content-creator-agent-api:latest`, `content-creator-agent-worker:latest` e `postgres:16-alpine` disponíveis:

```powershell
python tests/docker_hybrid/run.py
```

Se necessário, construa as imagens do projeto com `docker compose build api worker`. Os nomes das imagens podem ser ajustados pelas variáveis `HYBRID_DOCKER_API_IMAGE`, `HYBRID_DOCKER_WORKER_IMAGE` e `HYBRID_DOCKER_POSTGRES_IMAGE`. O ensaio usa uma rede e credenciais locais próprias, cria containers e tenta removê-los mesmo em caso de falha, verifica cliente antigo, isolamento de usuário, imagem herdada, edições concorrentes e resposta de callback perdida, reinicia a API para testar rollback e interrompe/reinicia a reconciliação com o S3 simulado pausado. Não usa as credenciais ou o bucket das aplicações.

Para executar os mesmos cenários usando um container LocalStack descartável em vez do simulador mínimo, com a imagem `localstack/localstack:3.8.1` disponível:

```powershell
$env:HYBRID_DOCKER_S3 = "localstack"
python tests/docker_hybrid/run.py
Remove-Item Env:HYBRID_DOCKER_S3
```

Nesse modo, a reconciliação com objetos de mais de 24 horas não é executada; ela continua coberta pelo modo padrão, que simula a idade dos objetos. Ambos os modos simulam a LLM. O ensaio não substitui a validação em ambiente de destino com AWS S3 e LLM reais, nem define metas de rollout.

### LocalStack para desenvolvimento

`docker-compose.localstack.yml` adiciona um S3 simulado e um bucket `postmind-local`. A inicialização e configuração estão documentadas em `docs/INTEGRATIONS.md`. A API usa o endpoint interno Docker para operações e o endpoint público `localhost:4566` para URLs acessadas pelo navegador; o worker usa o endpoint interno. Use apenas para desenvolvimento local.

Com o serviço ativo, o teste de integração do cliente Go cria e remove um objeto de teste no bucket local:

```powershell
$env:LOCALSTACK_TEST_ENDPOINT = "http://127.0.0.1:4566"
Push-Location apps/api
go test -tags=integration ./integration -run TestLocalStackS3RoundTrip -count=1
Pop-Location
Push-Location apps/worker
python -m pytest tests/test_localstack_assets.py -q
Pop-Location
Remove-Item Env:LOCALSTACK_TEST_ENDPOINT
```

O teste do worker verifica a escrita condicional, a repetição idempotente e a rejeição de conteúdo divergente. Ambos os testes aceitam apenas endpoints de loopback e não substitui o ensaio com AWS S3 real.
