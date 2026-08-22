SHELL := /bin/bash
COMPOSE ?= docker compose --env-file .env -f compose.yaml
LOCAL_COMPOSE ?= docker compose --env-file .env -f compose.yaml -f compose.local-build.yaml

.PHONY: help env up up-local down logs ps build-local compose-config migrate migrate-tenants bootstrap test lint backup restore validate health package
help:
	@printf '%s\n' \
	  'ARGWS Financial Platform' \
	  '  make env              cria .env e segredos' \
	  '  make up               deploy image-only: pull GHCR + up' \
	  '  make up-local         desenvolvimento explícito com build local' \
	  '  make build-local      somente constrói imagens locais' \
	  '  make compose-config   valida o Docker Compose de runtime' \
	  '  make down             para a stack sem remover dados' \
	  '  make logs             acompanha logs' \
	  '  make migrate          migrations Control Plane' \
	  '  make migrate-tenants  migrations de todos os tenants' \
	  '  make bootstrap        dados iniciais e administrador' \
	  '  make test             testes backend/frontend locais' \
	  '  make backup           backup completo' \
	  '  make validate         valida fontes e contratos de deploy' \
	  '  make package          gera ZIP/TAR.ZST limpos e verificáveis'

env:
	@test -f .env || cp .env.example .env
	python3 scripts/generate_secrets.py --env .env

up: env
	$(COMPOSE) config --quiet
	$(COMPOSE) pull
	$(COMPOSE) up -d --remove-orphans

build-local: env
	$(LOCAL_COMPOSE) build --pull

up-local: env
	$(LOCAL_COMPOSE) config --quiet
	$(LOCAL_COMPOSE) up -d --build --remove-orphans

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

test:
	PYTHONPATH=backend pytest -q backend/tests
	cd frontend && npm run typecheck && npm run test:run

lint:
	ruff check --config backend/pyproject.toml backend scripts

backup:
	./scripts/backup.sh

restore:
	@echo 'Use: ./scripts/restore.sh /caminho/backup.tar.zst[.age]'

validate:
	python3 -m compileall -q backend/app backend/migrations backend/tests scripts
	python3 scripts/validate_project.py
	python3 scripts/validate_runtime_contract.py
	node scripts/validate_frontend_syntax.mjs
	find . -type f -name '*.sh' -print0 | xargs -0 -n1 bash -n

package:
	python3 scripts/package_release.py --output-dir release-artifacts
