#!/usr/bin/env bash
set -Eeuo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
source "$ROOT/scripts/deploy/lib.sh"
DOMAIN="finance.argws.com.br"; EMAIL="infra@argws.com.br"; STACK_DIR=""; SITE_USER="financial"; CREATE_SITE=true; SKIP_UP=false
usage(){ cat <<USAGE
Uso: sudo ./deployments/cloudpanel/install.sh [--domain finance.argws.com.br] [--admin-email infra@argws.com.br] [opções]
  --stack-dir DIR        Diretório final da stack
  --site-user NOME       Usuário do Reverse Proxy CloudPanel
  --no-create-site       Não executar clpctl para criar o VHost principal
  --skip-up              Preparar sem iniciar containers

Modelo: um único Reverse Proxy finance.argws.com.br -> http://127.0.0.1:GATEWAY_PORT.
O mesmo VHost recebe *.finance.argws.com.br e o certificado wildcard.
USAGE
}
while (($#)); do case "$1" in
  --domain) DOMAIN="${2,,}"; shift 2;; --admin-email) EMAIL="${2,,}"; shift 2;;
  --stack-dir) STACK_DIR="$2"; shift 2;; --site-user) SITE_USER="$2"; shift 2;;
  --no-create-site) CREATE_SITE=false; shift;; --skip-up) SKIP_UP=true; shift;;
  -h|--help) usage; exit 0;; *) die "Opção desconhecida: $1";;
esac; done
[[ "$DOMAIN" == *.* ]] || die "--domain inválido"
[[ "$EMAIL" == *@* ]] || die "--admin-email inválido"
require_cmd python3; require_cmd tar
TARGET="${STACK_DIR:-$ROOT}"
sync_project "$ROOT" "$TARGET"
cd "$TARGET"
cp "$TARGET/deployments/cloudpanel/compose.yaml" "$TARGET/compose.yaml"
cp "$TARGET/deployments/cloudpanel/.env.example" "$TARGET/.env.example"
prepare_env "$TARGET" "$TARGET/.env.example" "$TARGET/.env" "$DOMAIN" "$EMAIL"
set_env .env APP_NAME "ARGWS Financial Platform"
set_env .env APP_PULL_POLICY always
set_env .env FINANCIAL_DATA_ROOT .
set_env .env COMPOSE_PROFILES cloudpanel
set_env .env PLATFORM_DOMAIN "$DOMAIN"
set_env .env CONTROL_PLANE_HOST "control.$DOMAIN"
set_env .env ADMIN_HOST "admin.$DOMAIN"
set_env .env API_HOST "api.$DOMAIN"
set_env .env DEMO_HOST "demo.$DOMAIN"
set_env .env TENANT_DOMAIN_ROOT "$DOMAIN"
set_env .env CLOUDPANEL_SITE_DOMAIN "$DOMAIN"
set_env .env CLOUDPANEL_WILDCARD_DOMAIN "*.$DOMAIN"
set_env .env CLOUDPANEL_SITE_USER "$SITE_USER"
set_env .env ACME_DOMAIN "$DOMAIN"
set_env .env ACME_EMAIL "$EMAIL"
set_env .env MONITORING_ENABLED true
mkdir -p data-postgres data-redis data-rabbitmq data-minio data-backups data-runtime data-celery data-prometheus data-grafana data-monitoring data-acme data-certs data-cloudpanel-agent secrets
touch secrets/rclone.conf secrets/backup-age-identity.txt
if $CREATE_SITE; then
  [[ $EUID -eq 0 ]] || die "Execute como root para automatizar o CloudPanel"
  require_cmd clpctl
  PORT="$(get_env .env GATEWAY_PORT)"
  SITE_PASS="$(get_env .env CLOUDPANEL_SITE_USER_PASSWORD)"
  if ! grep -RqsE "server_name[[:space:]].*${DOMAIN//./\\.}" /etc/nginx/sites-enabled 2>/dev/null; then
    log "Criando único Reverse Proxy: $DOMAIN -> 127.0.0.1:$PORT"
    clpctl site:add:reverse-proxy --domainName="$DOMAIN" --reverseProxyUrl="http://127.0.0.1:$PORT" --siteUser="$SITE_USER" --siteUserPassword="$SITE_PASS"
  else
    log "VHost principal já existe: $DOMAIN"
  fi
fi
export COMPOSE_FILE_PATH=compose.yaml
validate_project "$TARGET" true
if ! $SKIP_UP; then
  require_cmd docker
  docker compose version >/dev/null || die "Docker Compose v2 ausente"
  compose_cmd .env config --quiet
  compose_cmd .env pull
  compose_cmd .env up -d --remove-orphans
  wait_ready "$(get_env .env GATEWAY_PORT)" || {
    compose_cmd .env ps || true
    compose_cmd .env logs --tail=300 financial-preflight financial-migrate financial-api financial-gateway || true
    die "Readiness não ficou saudável"
  }
  compose_cmd .env ps
fi
cat <<OUT
ARGWS Financial Platform
Landing:       https://$DOMAIN
Demo:          https://demo.$DOMAIN
Control Plane: https://control.$DOMAIN
Admin alias:   https://admin.$DOMAIN
API:           https://api.$DOMAIN
Tenants:       https://<slug>.$DOMAIN
Gateway local: http://127.0.0.1:$(get_env .env GATEWAY_PORT)
OUT
