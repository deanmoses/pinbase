.PHONY: bootstrap dev test lint quality agent-docs api-gen ingest

bootstrap:
	./scripts/bootstrap

dev:
	./scripts/dev

test:
	./scripts/test

lint:
	./scripts/lint

quality: lint
	cd frontend && pnpm check
	@echo "All quality checks passed!"

agent-docs:
	python3 scripts/build_agent_docs.py

api-gen:
	cd backend && uv run python manage.py export_openapi_schema
	cd frontend && pnpm api:gen

ingest:
	cd backend && uv run python manage.py ingest_all
