#!/usr/bin/env bash
set -Eeuo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
source "$ROOT/scripts/deploy/lib.sh"
cd "$ROOT"
[[ -f .env ]] || die '.env ausente'

VERSION="${1:-}"
[[ -n "$VERSION" ]] || die 'Uso: rollback.sh <versao-ou-tag, ex.: 1.0.0-rc.3>'
VERSION="${VERSION#v}"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$ ]] || die 'Versão inválida'

cp "$ROOT/deployments/dockge/compose.yaml" "$ROOT/compose.yaml"
mkdir -p \
  data-postgres data-redis data-rabbitmq data-minio \
  data-backups data-runtime data-celery
chmod 0777 data-postgres data-redis data-rabbitmq data-minio
chmod 0770 data-backups data-runtime data-celery

export COMPOSE_FILE_PATH="compose.yaml"
set_env .env APP_PULL_POLICY always
set_env .env FINANCIAL_DATA_ROOT .
set_env .env BACKEND_IMAGE "ghcr.io/wkarts/argws-financial-api:$VERSION"
set_env .env FRONTEND_IMAGE "ghcr.io/wkarts/argws-financial-web:$VERSION"
set_env .env GATEWAY_IMAGE "ghcr.io/wkarts/argws-financial-gateway:$VERSION"

compose_cmd .env pull
compose_cmd .env up -d --remove-orphans
wait_ready "$(get_env .env GATEWAY_PORT)" || die 'Rollback não ficou saudável'
compose_cmd .env ps
log "Rollback concluído usando aliases imutáveis $VERSION. Execute update.sh para voltar ao canal latest."
