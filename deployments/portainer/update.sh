#!/usr/bin/env bash
set -Eeuo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
source "$ROOT/scripts/deploy/lib.sh"
ENV_FILE="${1:-$HERE/stack.env}"
[[ -f "$ENV_FILE" ]] || die "Arquivo de ambiente ausente: $ENV_FILE"
cd "$HERE"
require_cmd docker
docker compose -f stack.yaml --env-file "$ENV_FILE" pull
docker compose -f stack.yaml --env-file "$ENV_FILE" up -d --remove-orphans
PORT="$(get_env "$ENV_FILE" GATEWAY_PORT)"
wait_ready "${PORT:-8800}" || die 'Atualização Portainer não ficou saudável'
docker compose -f stack.yaml --env-file "$ENV_FILE" ps
