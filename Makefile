SHELL := /bin/bash
COMPOSE ?= docker compose

.PHONY: help env up down logs ps build migrate bootstrap test lint backup restore validate

help:
	@echo "ARGWS Financial Platform"
	@echo "  make env       - cria .env e gera segredos"
	@echo "  make up        - constrói e inicia a stack"
	@echo "  make down      - para a stack"
	@echo "  make logs      - acompanha os logs"
	@echo "  make migrate   - executa migrations do Control Plane"
	@echo "  make bootstrap - cria admin e tenant de demonstração"
	@echo "  make test      - executa testes backend e frontend"
	@echo "  make backup    - dispara backup completo"
	@echo "  make validate  - valida configuração e fontes"

env:
	@test -f .env || cp .env.example .env
	python3 scripts/generate_secrets.py --env .env

build:
	$(COMPOSE) build --pull

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

migrate:
	$(COMPOSE) run --rm financial-migrate

bootstrap:
	$(COMPOSE) run --rm financial-init

test:
	$(COMPOSE) --profile tools run --rm financial-api-test
	$(COMPOSE) --profile tools run --rm financial-web-test

lint:
	$(COMPOSE) run --rm financial-api ruff check app tests
	$(COMPOSE) run --rm financial-api mypy app

backup:
	$(COMPOSE) exec financial-worker celery -A app.workers.celery_app call app.tasks.backup_all

restore:
	@echo "Use: scripts/restore.sh /caminho/backup.tar.zst"

validate:
	python3 -m compileall -q backend/app backend/tests scripts
	python3 scripts/validate_project.py
