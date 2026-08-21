#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; source "$ROOT/scripts/deploy/lib.sh"; cd "$ROOT"
[[ -f .env ]] || die '.env ausente'; MODE="${1:-source}"; backup_before_update "$ROOT" .env
if [[ "$MODE" == images ]]; then export COMPOSE_FILE_PATH=deployments/docker/compose.images.yaml; compose_cmd .env pull; compose_cmd .env up -d --remove-orphans; else export COMPOSE_FILE_PATH=compose.yaml; compose_cmd .env build --pull; compose_cmd .env up -d --remove-orphans; fi
wait_ready "$(get_env .env GATEWAY_PORT)" || die 'Atualização falhou'
