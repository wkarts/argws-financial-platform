#!/usr/bin/env bash
set -Eeuo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
source "$ROOT/scripts/deploy/lib.sh"
DOMAIN="finance.argws.com.br"; EMAIL="infra@argws.com.br"; STACKS_DIR="${DOCKGE_STACKS_DIR:-/opt/stacks}"; STACK_NAME="argws-financial-platform"; SKIP_UP=false
usage(){ cat <<USAGE
Uso: ./deployments/dockge/install.sh [--domain finance.argws.com.br] [--admin-email infra@argws.com.br] [opções]
  --stacks-dir DIR   Diretório de stacks do Dockge (padrão: /opt/stacks)
  --stack-name NOME  Nome da stack
  --skip-up          Apenas prepara e valida os arquivos
USAGE
}
while (($#)); do case "$1" in
  --domain) DOMAIN="${2,,}"; shift 2;; --admin-email) EMAIL="${2,,}"; shift 2;;
  --stacks-dir) STACKS_DIR="$2"; shift 2;; --stack-name) STACK_NAME="$2"; shift 2;;
  --skip-up) SKIP_UP=true; shift;; -h|--help) usage; exit 0;; *) die "Opção desconhecida: $1";;
esac; done
[[ "$DOMAIN" == *.* ]] || die "--domain inválido"
[[ "$EMAIL" == *@* ]] || die "--admin-email inválido"
require_cmd python3; require_cmd tar
TARGET="$STACKS_DIR/$STACK_NAME"
sync_project "$ROOT" "$TARGET"
cd "$TARGET"
cp "$TARGET/deployments/dockge/compose.yaml" "$TARGET/compose.yaml"
cp "$TARGET/deployments/dockge/.env.example" "$TARGET/.env.example"
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
set_env .env BACKEND_IMAGE ghcr.io/wkarts/argws-financial-api:latest
set_env .env FRONTEND_IMAGE ghcr.io/wkarts/argws-financial-web:latest
set_env .env GATEWAY_IMAGE ghcr.io/wkarts/argws-financial-gateway:latest
mkdir -p data-postgres data-redis data-rabbitmq data-minio data-backups data-runtime data-celery data-prometheus data-grafana data-monitoring data-acme data-certs data-cloudpanel-agent secrets
touch secrets/rclone.conf secrets/backup-age-identity.txt
chmod 0777 data-postgres data-redis data-rabbitmq data-minio data-prometheus data-grafana
chmod 0770 data-backups data-runtime data-celery data-monitoring
chmod 0750 data-acme data-certs data-cloudpanel-agent
chmod 0700 secrets
chmod 0600 secrets/rclone.conf secrets/backup-age-identity.txt
export COMPOSE_FILE_PATH="compose.yaml"
validate_project "$TARGET" true
if ! $SKIP_UP; then
  require_cmd docker
  docker compose version >/dev/null || die "Docker Compose v2 ausente"
  compose_cmd .env config --quiet
  compose_cmd .env pull
  compose_cmd .env up -d --remove-orphans || {
    compose_cmd .env ps || true
    compose_cmd .env logs --tail=300 financial-preflight financial-migrate financial-minio-init financial-bootstrap || true
    die "Stack Dockge falhou durante preflight/migration/bootstrap"
  }
  wait_ready "$(get_env .env GATEWAY_PORT)" || {
    compose_cmd .env ps || true
    compose_cmd .env logs --tail=300 financial-preflight financial-migrate financial-api financial-bootstrap || true
    die "Stack Dockge não ficou saudável"
  }
fi
log "Stack preparada em $TARGET"
log "Landing: https://$DOMAIN"
log "Demo: https://demo.$DOMAIN"
log "Control Plane: https://control.$DOMAIN"
log "Admin alias: https://admin.$DOMAIN"
log "API: https://api.$DOMAIN"
log "Tenants: https://<slug>.$DOMAIN"
log "Persistência local: $TARGET/data-*"
log "Única porta publicada: 127.0.0.1:$(get_env .env GATEWAY_PORT) -> financial-gateway"
