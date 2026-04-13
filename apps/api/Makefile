# API HTTP (Echo). Copie .env.example para .env e ajuste variáveis.
# Migrations: usa `go run` (alinhado a go.mod); não exige `migrate` no PATH.
.PHONY: help run build test test-integration tidy fmt vet clean migrate migrate-up migrate-down migrate-version

BIN_DIR := bin
SERVER_BIN := $(BIN_DIR)/server
MIGRATE := go run -tags postgres github.com/golang-migrate/migrate/v4/cmd/migrate@v4.18.1

help:
	@echo "Comandos da API (content-creator-agent)"
	@echo ""
	@echo "  make run     — sobe o servidor (carrega .env se existir)"
	@echo "  make build   — compila o binário em $(SERVER_BIN)"
	@echo "  make test    — go test ./..."
	@echo "  make test-integration — go test -tags=integration ./integration/... (needs INTEGRATION_DATABASE_URL)"
	@echo "  make tidy    — go mod tidy"
	@echo "  make fmt     — go fmt ./..."
	@echo "  make vet     — go vet ./..."
	@echo "  make clean   — remove $(BIN_DIR)/"
	@echo ""
	@echo "Migrations (golang-migrate via go run; carrega .env se existir):"
	@echo "  make migrate / migrate-up  — aplica migrations (up)"
	@echo "  make migrate-down          — reverte 1 migration (down)"
	@echo "  make migrate-version       — mostra versão atual"
	@echo ""
	@echo "Variáveis obrigatórias: DATABASE_URL, JWT_SECRET, JWT_REFRESH_SECRET"
	@echo "(S3: AWS_REGION, AWS_S3_BUCKET ao subir o servidor.)"
	@echo "Async: WORKER_URL, WORKER_API_KEY; perfil: PROFILE_DATA_ROOT"
	@echo "Veja .env.example"

run:
	@bash -c 'set -a && [ -f .env ] && . ./.env; set +a; exec go run ./cmd/server'

# Carrega DATABASE_URL do .env (ou do ambiente já exportado).
migrate-up:
	@bash -c 'set -a && [ -f .env ] && . ./.env; set +a; \
		if [ -z "$$DATABASE_URL" ]; then echo "DATABASE_URL is not set"; exit 1; fi; \
		$(MIGRATE) -path internal/db/migrations -database "$$DATABASE_URL" up'

migrate-down:
	@bash -c 'set -a && [ -f .env ] && . ./.env; set +a; \
		if [ -z "$$DATABASE_URL" ]; then echo "DATABASE_URL is not set"; exit 1; fi; \
		$(MIGRATE) -path internal/db/migrations -database "$$DATABASE_URL" down 1'

migrate-version:
	@bash -c 'set -a && [ -f .env ] && . ./.env; set +a; \
		if [ -z "$$DATABASE_URL" ]; then echo "DATABASE_URL is not set"; exit 1; fi; \
		$(MIGRATE) -path internal/db/migrations -database "$$DATABASE_URL" version'

migrate: migrate-up

build: $(BIN_DIR)
	go build -o $(SERVER_BIN) ./cmd/server
	@echo "Binário: $(SERVER_BIN)"

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

test:
	go test ./...

test-integration:
	go test -tags=integration -v ./integration/...

tidy:
	go mod tidy

fmt:
	go fmt ./...

vet:
	go vet ./...

clean:
	rm -rf $(BIN_DIR)
