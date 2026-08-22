#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT/scripts/deploy/lib.sh"
cd "$ROOT"
[[ -f .env ]] || die '.env ausente'
require_cmd docker

VERSION="${1:-}"
[[ -n "$VERSION" ]] || die 'Uso: rollback.sh <versao-ou-tag, ex.: 1.0.0-rc.7>'
VERSION="${VERSION#v}"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$ ]] || die 'Versão inválida'

cp "$ROOT/deployments/dockge/compose.yaml" "$ROOT/compose.yaml"
mkdir -p data-postgres data-redis data-rabbitmq data-minio data-backups data-runtime data-celery secrets
: > secrets/rclone.conf
: > secrets/backup-age-identity.txt
chmod 0777 data-postgres data-redis data-rabbitmq data-minio
chmod 0770 data-backups data-runtime data-celery
chmod 0700 secrets
chmod 0600 secrets/rclone.conf secrets/backup-age-identity.txt

cat > .rollback.override.yaml <<EOF
services:
  financial-migrate:
    image: ghcr.io/wkarts/argws-financial-api:${VERSION}
    pull_policy: always
  financial-migrate-tenants:
    image: ghcr.io/wkarts/argws-financial-api:${VERSION}
    pull_policy: always
  financial-bootstrap:
    image: ghcr.io/wkarts/argws-financial-api:${VERSION}
    pull_policy: always
  financial-api:
    image: ghcr.io/wkarts/argws-financial-api:${VERSION}
    pull_policy: always
  financial-worker-default:
    image: ghcr.io/wkarts/argws-financial-api:${VERSION}
    pull_policy: always
  financial-worker-billing:
    image: ghcr.io/wkarts/argws-financial-api:${VERSION}
    pull_policy: always
  financial-worker-notifications:
    image: ghcr.io/wkarts/argws-financial-api:${VERSION}
    pull_policy: always
  financial-worker-backups:
    image: ghcr.io/wkarts/argws-financial-api:${VERSION}
    pull_policy: always
  financial-beat:
    image: ghcr.io/wkarts/argws-financial-api:${VERSION}
    pull_policy: always
  financial-web:
    image: ghcr.io/wkarts/argws-financial-web:${VERSION}
    pull_policy: always
  financial-gateway:
    image: ghcr.io/wkarts/argws-financial-gateway:${VERSION}
    pull_policy: always
EOF

# O preflight permanece em latest para validar a configuração atual antes de
# iniciar uma versão antiga. Isso também permite rollback para releases que
# ainda não continham app.preflight.
COMPOSE=(docker compose --env-file .env -f compose.yaml -f .rollback.override.yaml)
"${COMPOSE[@]}" config --quiet
"${COMPOSE[@]}" pull
"${COMPOSE[@]}" up -d --remove-orphans
wait_ready "$(get_env .env GATEWAY_PORT)" || {
  "${COMPOSE[@]}" logs --tail=250 financial-preflight financial-migrate financial-api || true
  die 'Rollback não ficou saudável'
}
"${COMPOSE[@]}" ps
log "Rollback temporário concluído em ${VERSION}. Execute update.sh para voltar integralmente ao GHCR :latest."
