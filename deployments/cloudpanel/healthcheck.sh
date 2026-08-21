#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; source "$ROOT/scripts/deploy/lib.sh"; cd "$ROOT"
[[ -f .env ]] || die ".env ausente"; compose_cmd .env ps
curl -fsS "http://127.0.0.1:$(get_env .env GATEWAY_PORT)/health/ready" | python3 -m json.tool
for host in "$(get_env .env PLATFORM_DOMAIN)" "$(get_env .env CONTROL_PLANE_HOST)" "$(get_env .env API_HOST)"; do curl -fsSI "https://$host/health/live" | head -n 1 || true; done
