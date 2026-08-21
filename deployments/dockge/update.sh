#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT/scripts/deploy/lib.sh"
cd "$ROOT"
[[ -f .env ]] || die ".env ausente"
require_cmd docker

# Reaplica o Compose image-only na raiz da stack. Assim os bind mounts ./data-*
# continuam relativos ao diretório gerenciado pelo Dockge.
cp "$ROOT/deployments/dockge/compose.yaml" "$ROOT/compose.yaml"
mkdir -p \
  data-postgres data-redis data-rabbitmq data-minio \
  data-backups data-runtime data-celery
chmod 0777 data-postgres data-redis data-rabbitmq data-minio
chmod 0770 data-backups data-runtime data-celery

export COMPOSE_FILE_PATH="compose.yaml"

mkdir -p .releases
STAMP="$(date +%Y%m%d%H%M%S)"
compose_cmd .env config > ".releases/compose-$STAMP.yaml"
cp .env ".releases/env-$STAMP"; chmod 0600 ".releases/env-$STAMP"
backup_before_update "$ROOT" .env

# Volta sempre ao canal operacional latest.
set_env .env APP_PULL_POLICY always
set_env .env FINANCIAL_DATA_ROOT .
set_env .env BACKEND_IMAGE ghcr.io/wkarts/argws-financial-api:latest
set_env .env FRONTEND_IMAGE ghcr.io/wkarts/argws-financial-web:latest
set_env .env GATEWAY_IMAGE ghcr.io/wkarts/argws-financial-gateway:latest
set_env .env ACME_IMAGE ghcr.io/wkarts/argws-financial-acme:latest
set_env .env CLOUDPANEL_AGENT_IMAGE ghcr.io/wkarts/argws-financial-cloudpanel-agent:latest

compose_cmd .env pull
compose_cmd .env up -d --remove-orphans
wait_ready "$(get_env .env GATEWAY_PORT)" || die "Atualização falhou no readiness; execute rollback.sh"
compose_cmd .env ps
