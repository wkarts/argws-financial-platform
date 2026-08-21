#!/usr/bin/env bash
set -Eeuo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
# shellcheck source=../../scripts/deploy/lib.sh
source "$ROOT/scripts/deploy/lib.sh"

DOMAIN=""; EMAIL=""; STACKS_DIR="${DOCKGE_STACKS_DIR:-/opt/stacks}"; STACK_NAME="argws-financial-platform"; SKIP_UP=false
usage(){ cat <<USAGE
Uso: ./deployments/dockge/install.sh --domain financeiro.exemplo.com.br --admin-email admin@exemplo.com.br [opções]
  --stacks-dir DIR   Diretório de stacks do Dockge (padrão: /opt/stacks)
  --stack-name NOME  Nome da stack
  --skip-up          Apenas prepara e valida os arquivos
USAGE
}
while (($#)); do case "$1" in
  --domain) DOMAIN="${2,,}"; shift 2;;
  --admin-email) EMAIL="${2,,}"; shift 2;;
  --stacks-dir) STACKS_DIR="$2"; shift 2;;
  --stack-name) STACK_NAME="$2"; shift 2;;
  --skip-up) SKIP_UP=true; shift;;
  -h|--help) usage; exit 0;;
  *) die "Opção desconhecida: $1";;
esac; done
[[ "$DOMAIN" == *.* ]] || die "--domain inválido"
[[ "$EMAIL" == *@* ]] || die "--admin-email inválido"
require_cmd python3; require_cmd tar
TARGET="$STACKS_DIR/$STACK_NAME"
sync_project "$ROOT" "$TARGET"
cd "$TARGET"
prepare_env "$TARGET" "$TARGET/.env.example" "$TARGET/.env" "$DOMAIN" "$EMAIL"
validate_project "$TARGET" true

if ! $SKIP_UP; then
  require_cmd docker
  docker compose version >/dev/null || die "Docker Compose v2 ausente"
  compose_cmd .env config --quiet
  compose_cmd .env up -d --build --remove-orphans
  wait_ready "$(get_env .env GATEWAY_PORT)" || {
    compose_cmd .env ps || true
    compose_cmd .env logs --tail=250 financial-api financial-migrate financial-bootstrap || true
    die "Stack Dockge não ficou saudável"
  }
fi
log "Stack preparada em $TARGET"
log "No Dockge, use Scan Stacks Folder e abra '$STACK_NAME'."
printf 'Control Plane: https://control.%s\nTenant: https://<slug>.%s\nCredenciais: %s/.bootstrap-credentials.txt\n' "$DOMAIN" "$DOMAIN" "$TARGET"
