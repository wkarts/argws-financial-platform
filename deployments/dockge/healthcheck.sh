#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT/scripts/deploy/lib.sh"
cd "$ROOT"
[[ -f .env ]] || die ".env ausente"

cp "$ROOT/deployments/dockge/compose.yaml" "$ROOT/compose.yaml"
export COMPOSE_FILE_PATH="compose.yaml"
compose_cmd .env ps
curl -fsS "http://127.0.0.1:$(get_env .env GATEWAY_PORT)/health/ready" | python3 -m json.tool
