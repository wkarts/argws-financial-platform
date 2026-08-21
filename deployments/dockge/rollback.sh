#!/usr/bin/env bash
set -Eeuo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
source "$ROOT/scripts/deploy/lib.sh"
cd "$ROOT"
[[ -f .env ]] || die '.env ausente'
VERSION="${1:-}"
[[ -n "$VERSION" ]] || die 'Uso: rollback.sh <APP_VERSION-ou-tag>'
set_env .env APP_VERSION "$VERSION"
set_env .env APP_PULL_POLICY always
compose_cmd .env pull || true
compose_cmd .env up -d --remove-orphans
wait_ready "$(get_env .env GATEWAY_PORT)" || die 'Rollback não ficou saudável'
compose_cmd .env ps
