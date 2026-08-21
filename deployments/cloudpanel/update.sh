#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; source "$ROOT/scripts/deploy/lib.sh"; cd "$ROOT"
[[ -f .env ]] || die ".env ausente"; require_cmd docker
mkdir -p .releases; STAMP="$(date +%Y%m%d%H%M%S)"
compose_cmd .env config > ".releases/compose-$STAMP.yaml"; cp .env ".releases/env-$STAMP"; chmod 600 ".releases/env-$STAMP"
backup_before_update "$ROOT" .env
compose_cmd .env build --pull; compose_cmd .env up -d --remove-orphans
wait_ready "$(get_env .env GATEWAY_PORT)" || die "Atualização falhou; use rollback.sh"
compose_cmd .env ps
