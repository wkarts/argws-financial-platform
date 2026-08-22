#!/usr/bin/env bash
set -Eeuo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
source "$ROOT/scripts/deploy/lib.sh"

DOMAIN=""; EMAIL=""; STACK_DIR=""; SITE_USER="financial"; CREATE_SITES=true; SKIP_UP=false
usage(){ cat <<USAGE
Uso: sudo ./deployments/cloudpanel/install.sh --domain financeiro.exemplo.com.br --admin-email admin@exemplo.com.br [opções]
  --stack-dir DIR        Diretório final da stack
  --site-user NOME       Usuário dos reverse proxies CloudPanel
  --no-create-sites      Não executar clpctl
  --skip-up              Preparar sem iniciar containers

O runtime é exclusivamente image-only. Somente 127.0.0.1:GATEWAY_PORT é
publicado no host; PostgreSQL, Redis, RabbitMQ, MinIO e demais serviços ficam
somente na rede interna Docker.
USAGE
}
while (($#)); do case "$1" in
  --domain) DOMAIN="${2,,}"; shift 2;; --admin-email) EMAIL="${2,,}"; shift 2;;
  --stack-dir) STACK_DIR="$2"; shift 2;; --site-user) SITE_USER="$2"; shift 2;;
  --no-create-sites) CREATE_SITES=false; shift;; --skip-up) SKIP_UP=true; shift;;
  --enable-acme|--enable-monitoring) die "$1 não é mais exposto pelo runtime; use CloudPanel/Cloudflare ou ferramenta interna dedicada";;
  -h|--help) usage; exit 0;; *) die "Opção desconhecida: $1";;
esac; done
[[ "$DOMAIN" == *.* ]] || die "--domain inválido"
[[ "$EMAIL" == *@* ]] || die "--admin-email inválido"
require_cmd python3; require_cmd tar
TARGET="${STACK_DIR:-$ROOT}"
sync_project "$ROOT" "$TARGET"
cd "$TARGET"
prepare_env "$TARGET" "$TARGET/.env.example" "$TARGET/.env" "$DOMAIN" "$EMAIL"
set_env .env CLOUDPANEL_SITE_USER "$SITE_USER"
set_env .env APP_PULL_POLICY always
set_env .env FINANCIAL_DATA_ROOT .
set_env .env ACME_ENABLED false
set_env .env CLOUDPANEL_AGENT_ENABLED false
set_env .env MONITORING_ENABLED false
set_env .env BACKEND_IMAGE ghcr.io/wkarts/argws-financial-api:latest
set_env .env FRONTEND_IMAGE ghcr.io/wkarts/argws-financial-web:latest
set_env .env GATEWAY_IMAGE ghcr.io/wkarts/argws-financial-gateway:latest

if $CREATE_SITES; then
  [[ $EUID -eq 0 ]] || die "Execute como root para automatizar o CloudPanel"
  require_cmd clpctl
  SITE_PASS="$(get_env .env CLOUDPANEL_SITE_USER_PASSWORD)"
  PORT="$(get_env .env GATEWAY_PORT)"
  for host in "$DOMAIN" "control.$DOMAIN" "api.$DOMAIN"; do
    if ! grep -RqsE "server_name[[:space:]].*${host//./\\.}" /etc/nginx/sites-enabled 2>/dev/null; then
      log "Criando reverse proxy CloudPanel: $host -> 127.0.0.1:$PORT"
      clpctl site:add:reverse-proxy --domainName="$host" --reverseProxyUrl="http://127.0.0.1:$PORT" --siteUser="$SITE_USER" --siteUserPassword="$SITE_PASS"
    else
      log "VHost já existente: $host"
    fi
  done
  python3 - "$DOMAIN" <<'PY'
from pathlib import Path
import re, shutil, subprocess, sys, time
domain=sys.argv[1]; wildcard='*.'+domain
files=sorted(Path('/etc/nginx/sites-enabled').glob('*.conf'))
match=None
for p in files:
    text=p.read_text(encoding='utf-8', errors='ignore')
    if re.search(r'\bserver_name\s+[^;]*\b'+re.escape(domain)+r'\b', text):
        match=p; break
if match:
    original=match.read_text(encoding='utf-8')
    def patch(m):
        content=m.group(1)
        return m.group(0) if wildcard in content.split() else 'server_name '+content.strip()+' '+wildcard+';'
    updated=re.sub(r'server_name\s+([^;]+);', patch, original)
    if updated != original:
        backup=match.with_suffix(match.suffix+f'.pre-financial-{int(time.time())}.bak')
        shutil.copy2(match, backup); match.write_text(updated, encoding='utf-8')
        if subprocess.run(['nginx','-t'],capture_output=True).returncode != 0:
            shutil.copy2(backup, match); raise SystemExit('nginx -t falhou; vhost restaurado')
        subprocess.run(['nginx','-s','reload'],check=False)
PY
fi

export COMPOSE_FILE_PATH=compose.yaml
validate_project "$TARGET" true
if ! $SKIP_UP; then
  require_cmd docker; docker compose version >/dev/null || die "Docker Compose v2 ausente"
  compose_cmd .env config --quiet
  compose_cmd .env pull
  compose_cmd .env up -d --remove-orphans
  PORT="$(get_env .env GATEWAY_PORT)"
  wait_ready "$PORT" || {
    compose_cmd .env ps || true
    compose_cmd .env logs --tail=250 financial-preflight financial-migrate financial-api financial-bootstrap || true
    die "Readiness não ficou saudável"
  }
  if $CREATE_SITES; then
    for host in "$DOMAIN" "control.$DOMAIN" "api.$DOMAIN"; do
      clpctl lets-encrypt:install:certificate --domainName="$host" || warn "SSL pendente para $host"
    done
    warn "Para HTTPS wildcard de tenants, use certificado wildcard/origin válido no CloudPanel/Cloudflare."
  fi
  compose_cmd .env ps
fi
cat <<OUT

Stack:         $TARGET
Gateway local: http://127.0.0.1:$(get_env .env GATEWAY_PORT)
Plataforma:    https://$DOMAIN
Control Plane: https://control.$DOMAIN
API/Docs:      https://api.$DOMAIN/api/docs
Tenants:       https://<slug>.$DOMAIN
Credenciais:   $TARGET/.bootstrap-credentials.txt
OUT
