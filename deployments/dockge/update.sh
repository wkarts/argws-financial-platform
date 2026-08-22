#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT/scripts/deploy/lib.sh"
cd "$ROOT"
[[ -f .env ]] || die ".env ausente"
require_cmd docker

cp "$ROOT/deployments/dockge/compose.yaml" "$ROOT/compose.yaml"
rm -f "$ROOT/.rollback.override.yaml"
mkdir -p \
  data-postgres data-redis data-rabbitmq data-minio \
  data-backups data-runtime data-celery secrets
: > secrets/rclone.conf
: > secrets/backup-age-identity.txt
chmod 0777 data-postgres data-redis data-rabbitmq data-minio
chmod 0770 data-backups data-runtime data-celery
chmod 0700 secrets
chmod 0600 secrets/rclone.conf secrets/backup-age-identity.txt

export COMPOSE_FILE_PATH="compose.yaml"

mkdir -p .releases
STAMP="$(date +%Y%m%d%H%M%S)"
compose_cmd .env config > ".releases/compose-$STAMP.yaml"
cp .env ".releases/env-$STAMP"; chmod 0600 ".releases/env-$STAMP"
backup_before_update "$ROOT" .env

set_env .env APP_PULL_POLICY always
set_env .env FINANCIAL_DATA_ROOT .
set_env .env BACKEND_IMAGE ghcr.io/wkarts/argws-financial-api:latest
set_env .env FRONTEND_IMAGE ghcr.io/wkarts/argws-financial-web:latest
set_env .env GATEWAY_IMAGE ghcr.io/wkarts/argws-financial-gateway:latest

compose_cmd .env config --quiet
compose_cmd .env pull
compose_cmd .env up -d --remove-orphans
wait_ready "$(get_env .env GATEWAY_PORT)" || {
  compose_cmd .env logs --tail=250 financial-preflight financial-migrate financial-api || true
  die "Atualização falhou no readiness; corrija o preflight/migration ou execute rollback.sh"
}
compose_cmd .env ps
