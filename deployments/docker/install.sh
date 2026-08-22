#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT/scripts/deploy/lib.sh"
cd "$ROOT"

DOMAIN=""
EMAIL=""
SKIP_UP=false

usage(){ cat <<'USAGE'
Uso: install.sh --domain DOMINIO --admin-email EMAIL [--skip-up]

Este instalador é exclusivamente image-only e consome GHCR :latest.
Build local não é modo de deploy. Para desenvolvimento local use:
  docker compose -f compose.yaml -f compose.local-build.yaml up -d --build
USAGE
}

while (($#)); do
  case "$1" in
    --domain) DOMAIN="${2,,}"; shift 2 ;;
    --admin-email) EMAIL="${2,,}"; shift 2 ;;
    --skip-up) SKIP_UP=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Opção desconhecida: $1" ;;
  esac
done

[[ "$DOMAIN" == *.* ]] || die '--domain inválido'
[[ "$EMAIL" == *@* ]] || die '--admin-email inválido'

[[ -f .env ]] || cp .env.example .env
prepare_env "$ROOT" "$ROOT/.env.example" "$ROOT/.env" "$DOMAIN" "$EMAIL"
version="$(canonical_version "$ROOT")"

set_env .env APP_PULL_POLICY always
set_env .env FINANCIAL_DATA_ROOT .
set_env .env BACKEND_IMAGE "ghcr.io/wkarts/argws-financial-api:latest"
set_env .env FRONTEND_IMAGE "ghcr.io/wkarts/argws-financial-web:latest"
set_env .env GATEWAY_IMAGE "ghcr.io/wkarts/argws-financial-gateway:latest"
set_env .env ACME_IMAGE "ghcr.io/wkarts/argws-financial-acme:latest"
set_env .env CLOUDPANEL_AGENT_IMAGE "ghcr.io/wkarts/argws-financial-cloudpanel-agent:latest"

export COMPOSE_FILE_PATH=compose.yaml
validate_project "$ROOT" true

$SKIP_UP && {
  log "Configuração image-only preparada para $version, sem subir containers."
  exit 0
}

require_cmd docker
docker compose version >/dev/null || die 'Docker Compose v2 ausente'
compose_cmd .env config --quiet
log "Baixando imagens GHCR latest para $version"
compose_cmd .env pull
compose_cmd .env up -d --remove-orphans

wait_ready "$(get_env .env GATEWAY_PORT)" || {
  compose_cmd .env ps || true
  compose_cmd .env logs --tail=300 financial-preflight financial-migrate financial-api financial-web financial-gateway || true
  die 'Stack não ficou saudável'
}

compose_cmd .env ps
