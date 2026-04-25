# Root orchestration: E2E against Docker Compose (real worker + LLM + S3).
.PHONY: e2e prod-up prod-down

e2e:
	docker compose up -d --build --wait
	cd tests/e2e && pip install -r requirements.txt -q && pytest -v
	docker compose down

prod-up:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build --wait

prod-down:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down
