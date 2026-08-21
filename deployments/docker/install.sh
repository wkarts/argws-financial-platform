#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT/scripts/deploy/lib.sh"
cd "$ROOT"

DOMAIN=""
EMAIL=""
MODE=source
SKIP_UP=false

while (($#)); do
  case "$1" in
    --domain) DOMAIN="${2,,}"; shift 2 ;;
    --admin-email) EMAIL="${2,,}"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --skip-up) SKIP_UP=true; shift ;;
    -h|--help)
      echo 'Uso: install.sh --domain DOMINIO --admin-email EMAIL [--mode source|images] [--skip-up]'
      exit 0
      ;;
    *) die "Opção desconhecida: $1" ;;
  esac
done

[[ "$DOMAIN" == *.* ]] || die '--domain inválido'
[[ "$EMAIL" == *@* ]] || die '--admin-email inválido'
[[ "$MODE" =~ ^(source|images)$ ]] || die '--mode deve ser source ou images'

[[ -f .env ]] || cp .env.example .env
prepare_env "$ROOT" "$ROOT/.env.example" "$ROOT/.env" "$DOMAIN" "$EMAIL"
version="$(canonical_version "$ROOT")"

if [[ "$MODE" == images ]]; then
  COMPOSE_FILE_PATH=deployments/docker/compose.images.yaml
  set_env .env APP_PULL_POLICY always
  set_env .env BACKEND_IMAGE "ghcr.io/wkarts/argws-financial-api:latest"
  set_env .env FRONTEND_IMAGE "ghcr.io/wkarts/argws-financial-web:latest"
  set_env .env GATEWAY_IMAGE "ghcr.io/wkarts/argws-financial-gateway:latest"
  set_env .env ACME_IMAGE "ghcr.io/wkarts/argws-financial-acme:latest"
  set_env .env CLOUDPANEL_AGENT_IMAGE "ghcr.io/wkarts/argws-financial-cloudpanel-agent:latest"
else
  COMPOSE_FILE_PATH=compose.yaml
  set_env .env APP_PULL_POLICY build
  set_env .env BACKEND_IMAGE "argws-financial-api:latest"
  set_env .env FRONTEND_IMAGE "argws-financial-web:latest"
  set_env .env GATEWAY_IMAGE "argws-financial-gateway:latest"
  set_env .env ACME_IMAGE "argws-financial-acme:latest"
  set_env .env CLOUDPANEL_AGENT_IMAGE "argws-financial-cloudpanel-agent:latest"
fi

export COMPOSE_FILE_PATH
validate_project "$ROOT" true

$SKIP_UP && {
  log "Configuração preparada em modo '$MODE' para a aplicação $version, sem subir containers."
  exit 0
}

require_cmd docker
docker compose version >/dev/null || die 'Docker Compose v2 ausente'
compose_cmd .env config --quiet

if [[ "$MODE" == images ]]; then
  log "Baixando imagens latest do GHCR para executar a aplicação $version"
  compose_cmd .env pull
  compose_cmd .env up -d --remove-orphans
else
  log "Construindo imagens latest localmente a partir do código-fonte da aplicação $version"
  compose_cmd .env up -d --build --remove-orphans
fi

wait_ready "$(get_env .env GATEWAY_PORT)" || {
  compose_cmd .env ps || true
  compose_cmd .env logs --tail=300 financial-api financial-web financial-gateway || true
  die 'Stack não ficou saudável'
}

compose_cmd .env ps
