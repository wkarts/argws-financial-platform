#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
PLATFORM_DOMAIN=""
ADMIN_EMAIL=""
CLOUDFLARE_ZONE=""
STACK_DIR=""
SKIP_UP=false

usage() {
  cat <<'USAGE'
Uso:
  ./scripts/deploy_cloudpanel_dockge.sh \
    --domain financeiro.exemplo.com.br \
    --admin-email admin@exemplo.com.br \
    [--cloudflare-zone exemplo.com.br] \
    [--stack-dir /home/USUARIO/htdocs/DOMINIO/dockge-stacks/argws-financial-platform] \
    [--skip-up]

--domain é o domínio-base completo da plataforma. Os hosts serão:
  financeiro.exemplo.com.br            site/plataforma
  control.financeiro.exemplo.com.br    Control Plane
  api.financeiro.exemplo.com.br        API central, saúde e documentação
  <slug>.financeiro.exemplo.com.br     tenants provisionados
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain|--platform-domain) PLATFORM_DOMAIN="$2"; shift 2 ;;
    --admin-email) ADMIN_EMAIL="$2"; shift 2 ;;
    --cloudflare-zone) CLOUDFLARE_ZONE="$2"; shift 2 ;;
    --stack-dir) STACK_DIR="$2"; shift 2 ;;
    --skip-up) SKIP_UP=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opção desconhecida: $1" >&2; usage; exit 2 ;;
  esac
done

PLATFORM_DOMAIN="${PLATFORM_DOMAIN,,}"
PLATFORM_DOMAIN="${PLATFORM_DOMAIN%.}"
CLOUDFLARE_ZONE="${CLOUDFLARE_ZONE,,}"
CLOUDFLARE_ZONE="${CLOUDFLARE_ZONE%.}"

[[ -n "$PLATFORM_DOMAIN" && "$PLATFORM_DOMAIN" == *.* ]] || { echo "--domain inválido ou ausente." >&2; exit 2; }
[[ -n "$ADMIN_EMAIL" && "$ADMIN_EMAIL" == *@* ]] || { echo "--admin-email inválido ou ausente." >&2; exit 2; }
command -v python3 >/dev/null || { echo "python3 não instalado." >&2; exit 1; }

if [[ -z "$CLOUDFLARE_ZONE" ]]; then
  CLOUDFLARE_ZONE="${PLATFORM_DOMAIN#*.}"
fi

if ! $SKIP_UP; then
  command -v docker >/dev/null || { echo "Docker não instalado." >&2; exit 1; }
  docker compose version >/dev/null || { echo "Docker Compose v2 não instalado." >&2; exit 1; }
fi

TARGET="$ROOT_DIR"
if [[ -n "$STACK_DIR" ]]; then
  mkdir -p "$STACK_DIR"
  TARGET="$(realpath "$STACK_DIR")"
  if [[ "$TARGET" != "$ROOT_DIR" ]]; then
    tar \
      --exclude='.git' \
      --exclude='.env' \
      --exclude='.bootstrap-credentials.txt' \
      --exclude='__pycache__' \
      --exclude='.pytest_cache' \
      -cf - . | tar -xf - -C "$TARGET"
  fi
fi

cd "$TARGET"
cp -n .env.example .env
python3 - "$PLATFORM_DOMAIN" "$ADMIN_EMAIL" "$CLOUDFLARE_ZONE" <<'PY'
from pathlib import Path
import sys

path = Path('.env')
domain = sys.argv[1].lower().strip('.')
email = sys.argv[2].lower().strip()
zone = sys.argv[3].lower().strip('.')

values = {
    'PLATFORM_DOMAIN': domain,
    'CONTROL_PLANE_HOST': f'control.{domain}',
    'API_HOST': f'api.{domain}',
    'TENANT_DOMAIN_ROOT': domain,
    'PLATFORM_ADMIN_EMAIL': email,
    'CLOUDFLARE_ZONE_NAME': zone,
    'CLOUDFLARE_TENANT_RECORD_TARGET': domain,
    'ACME_EMAIL': email,
    'SMTP_FROM_EMAIL': f'financeiro@{zone}',
    'VITE_CONTROL_PLANE_HOST': f'control.{domain}',
    'TRUSTED_HOSTS': ','.join([
        domain,
        f'control.{domain}',
        f'api.{domain}',
        f'.{domain}',
        'localhost',
        '127.0.0.1',
    ]),
    'CORS_ORIGINS': ','.join([f'https://{domain}', f'https://control.{domain}']),
}

output: list[str] = []
for line in path.read_text(encoding='utf-8').splitlines():
    key = line.split('=', 1)[0] if '=' in line else ''
    output.append(f'{key}={values[key]}' if key in values else line)
path.write_text('\n'.join(output) + '\n', encoding='utf-8')
PY

python3 scripts/generate_secrets.py --env .env
python3 scripts/validate_project.py --allow-runtime-files

if ! $SKIP_UP; then
  docker compose config --quiet
  docker compose build --pull
  docker compose up -d

  gateway_port="$(grep '^GATEWAY_PORT=' .env | cut -d= -f2)"
  ready=false
  for _ in $(seq 1 90); do
    if curl -fsS "http://127.0.0.1:${gateway_port}/health/ready" >/dev/null 2>&1; then
      ready=true
      break
    fi
    sleep 2
  done
  if ! $ready; then
    echo "A API não ficou pronta. Estado e logs:" >&2
    docker compose ps >&2 || true
    docker compose logs --tail=200 financial-api financial-migrate financial-init >&2 || true
    exit 1
  fi
  docker compose ps
fi

cat <<OUT

Stack preparada em: $TARGET
Gateway interno: http://127.0.0.1:$(grep '^GATEWAY_PORT=' .env | cut -d= -f2)
Plataforma: https://$(grep '^PLATFORM_DOMAIN=' .env | cut -d= -f2)
Control Plane: https://$(grep '^CONTROL_PLANE_HOST=' .env | cut -d= -f2)
API central/saúde/docs: https://$(grep '^API_HOST=' .env | cut -d= -f2)
Tenants e APIs/webhooks isolados: https://<slug>.$(grep '^TENANT_DOMAIN_ROOT=' .env | cut -d= -f2)
Credenciais iniciais: $TARGET/.bootstrap-credentials.txt

No CloudPanel, configure o domínio-base, control, api e o wildcard *.$(grep '^TENANT_DOMAIN_ROOT=' .env | cut -d= -f2)
como proxies reversos para o gateway interno, preservando o cabeçalho Host.
Consulte docs/operations/DEPLOY_CLOUDPANEL_DOCKGE.md.
OUT
