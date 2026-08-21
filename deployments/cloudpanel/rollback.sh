#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; source "$ROOT/scripts/deploy/lib.sh"; cd "$ROOT"
[[ -f .env ]] || die ".env ausente"; VERSION="${1:-}"; [[ -n "$VERSION" ]] || die "Uso: rollback.sh <versão>"
set_env .env APP_VERSION "$VERSION"; set_env .env BACKEND_IMAGE "ghcr.io/wkarts/argws-financial-api:$VERSION"; set_env .env FRONTEND_IMAGE "ghcr.io/wkarts/argws-financial-web:$VERSION"; set_env .env APP_PULL_POLICY always
compose_cmd .env pull; compose_cmd .env up -d --remove-orphans
wait_ready "$(get_env .env GATEWAY_PORT)" || die "Rollback não ficou saudável"
