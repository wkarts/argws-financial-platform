#!/usr/bin/env bash
set -Eeuo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
source "$ROOT/scripts/deploy/lib.sh"

DOMAIN="${PORTAINER_DOMAIN:-finance.argws.com.br}"
EMAIL="${PORTAINER_ADMIN_EMAIL:-admin@finance.argws.com.br}"
ENV_FILE="$HERE/stack.env"
LOCAL=false
INSECURE=false
PREPARE_ONLY=false
PORTAINER_URL="${PORTAINER_URL:-}"
PORTAINER_API_KEY="${PORTAINER_API_KEY:-}"
ENDPOINT_ID="${PORTAINER_ENDPOINT_ID:-1}"
STACK_NAME="${PORTAINER_STACK_NAME:-argws-financial-platform}"

usage(){ cat <<USAGE
Uso: ./deployments/portainer/deploy.sh [--domain finance.argws.com.br] [--admin-email admin@finance.argws.com.br] [opções]
  --url URL             URL do Portainer
  --api-key CHAVE       API key Portainer
  --endpoint-id ID      Endpoint Docker (padrão: 1)
  --stack-name NOME     Nome da stack
  --env-file ARQUIVO    Arquivo de ambiente gerado
  --local               Executar pelo Docker Compose local em vez da API
  --prepare-only        Gerar ambiente e validar sem chamar Docker/Portainer
  --insecure            Ignorar validação TLS da API Portainer

Runtime: image-only / GHCR latest. Nenhum build ocorre no servidor.
USAGE
}

while (($#)); do
  case "$1" in
    --domain) DOMAIN="${2,,}"; shift 2 ;;
    --admin-email) EMAIL="${2,,}"; shift 2 ;;
    --url) PORTAINER_URL="$2"; shift 2 ;;
    --api-key) PORTAINER_API_KEY="$2"; shift 2 ;;
    --endpoint-id) ENDPOINT_ID="$2"; shift 2 ;;
    --stack-name) STACK_NAME="$2"; shift 2 ;;
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --local) LOCAL=true; shift ;;
    --prepare-only) PREPARE_ONLY=true; shift ;;
    --insecure) INSECURE=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Opção desconhecida: $1" ;;
  esac
done

[[ "$DOMAIN" == *.* ]] || die "--domain inválido"
[[ "$EMAIL" == *@* ]] || die "--admin-email inválido"
require_cmd python3

[[ -f "$ENV_FILE" ]] || cp "$ROOT/deployments/portainer/stack.env.example" "$ENV_FILE"
prepare_env "$ROOT" "$ROOT/deployments/portainer/stack.env.example" "$ENV_FILE" "$DOMAIN" "$EMAIL"
version="$(canonical_version "$ROOT")"
set_env "$ENV_FILE" APP_NAME "ARGWS Financial Platform"
set_env "$ENV_FILE" APP_PULL_POLICY always
set_env "$ENV_FILE" FINANCIAL_DATA_ROOT .
set_env "$ENV_FILE" BACKEND_IMAGE "ghcr.io/wkarts/argws-financial-api:latest"
set_env "$ENV_FILE" FRONTEND_IMAGE "ghcr.io/wkarts/argws-financial-web:latest"
set_env "$ENV_FILE" GATEWAY_IMAGE "ghcr.io/wkarts/argws-financial-gateway:latest"
set_env "$ENV_FILE" ACME_IMAGE "ghcr.io/wkarts/argws-financial-acme:latest"
set_env "$ENV_FILE" CLOUDPANEL_AGENT_IMAGE "ghcr.io/wkarts/argws-financial-cloudpanel-agent:latest"
chmod 600 "$ENV_FILE"
validate_project "$ROOT" true

if $PREPARE_ONLY; then
  log "Ambiente Portainer preparado e validado: $ENV_FILE"
  log "Versão da aplicação: $version"
  log "Domínio padrão: $DOMAIN"
  log "Imagens: GHCR latest"
  log "Stack: $HERE/stack.yaml"
  exit 0
fi

if $LOCAL; then
  require_cmd docker
  docker compose version >/dev/null || die "Docker Compose v2 ausente"
  COMPOSE_FILE_PATH="$HERE/stack.yaml" compose_cmd "$ENV_FILE" config --quiet
  COMPOSE_FILE_PATH="$HERE/stack.yaml" compose_cmd "$ENV_FILE" pull
  COMPOSE_FILE_PATH="$HERE/stack.yaml" compose_cmd "$ENV_FILE" up -d --remove-orphans
  wait_ready "$(get_env "$ENV_FILE" GATEWAY_PORT)" || die "Stack local não ficou saudável"
  exit 0
fi

[[ -n "$PORTAINER_URL" ]] || die "PORTAINER_URL/--url obrigatório"
[[ -n "$PORTAINER_API_KEY" ]] || die "PORTAINER_API_KEY/--api-key obrigatório"
args=(--url "$PORTAINER_URL" --api-key "$PORTAINER_API_KEY" --endpoint-id "$ENDPOINT_ID" --stack-name "$STACK_NAME" --stack-file "$HERE/stack.yaml" --env-file "$ENV_FILE")
$INSECURE && args+=(--insecure)
python3 "$ROOT/scripts/portainer_deploy.py" "${args[@]}"
log "Stack Portainer criada/atualizada: $STACK_NAME"
log "ARGWS Financial Platform $version"
log "Landing: https://$DOMAIN"
log "Demo: https://demo.$DOMAIN"
log "Control Plane: https://control.$DOMAIN"
log "API: https://api.$DOMAIN"
