# Root orchestration: E2E against Docker Compose (real worker + LLM + S3).
.PHONY: e2e

e2e:
	docker compose up -d --build --wait
	cd tests/e2e && pip install -r requirements.txt -q && pytest -v
	docker compose down
