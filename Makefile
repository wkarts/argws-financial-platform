SHELL := /bin/bash
COMPOSE ?= docker compose --env-file .env -f compose.yaml

.PHONY: help env up down logs ps build compose-config migrate migrate-tenants bootstrap test lint backup restore validate health package
help:
	@printf '%s\n' \
	  'ARGWS Financial Platform' \
	  '  make env              cria .env e segredos' \
	  '  make up               inicia a stack completa' \
	  '  make compose-config   valida o Docker Compose' \
	  '  make down             para a stack' \
	  '  make logs             acompanha logs' \
	  '  make migrate          migrations Control Plane' \
	  '  make migrate-tenants  migrations de todos os tenants' \
	  '  make bootstrap        dados iniciais e administrador' \
	  '  make test             testes backend/frontend em containers' \
	  '  make backup           backup completo' \
	  '  make validate         valida fontes e contratos de deploy' \
	  '  make package          gera ZIP/TAR.ZST limpos e verificáveis'

env:
	@test -f .env || cp .env.example .env
	python3 scripts/generate_secrets.py --env .env

build: env
	$(COMPOSE) build --pull

up: env
	$(COMPOSE) up -d --build --remove-orphans

compose-config: env
	$(COMPOSE) config --quiet

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

health:
	./deployments/dockge/healthcheck.sh

migrate:
	$(COMPOSE) run --rm financial-migrate

migrate-tenants:
	$(COMPOSE) run --rm financial-migrate-tenants

bootstrap:
	$(COMPOSE) run --rm financial-bootstrap

test: env
	$(COMPOSE) --profile tools run --rm financial-api-test
	$(COMPOSE) --profile tools run --rm financial-web-test

lint: env
	$(COMPOSE) --profile tools run --rm financial-api-test ruff check app tests
	$(COMPOSE) --profile tools run --rm financial-api-test mypy app

backup:
	./scripts/backup.sh

restore:
	@echo 'Use: ./scripts/restore.sh /caminho/backup.tar.zst[.age]'

validate:
	python3 -m compileall -q backend/app backend/migrations backend/tests scripts
	python3 scripts/validate_project.py
	node scripts/validate_frontend_syntax.mjs
	find . -type f -name '*.sh' -print0 | xargs -0 -n1 bash -n

package:
	python3 scripts/package_release.py --output-dir release-artifacts
