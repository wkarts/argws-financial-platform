#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
command -v docker >/dev/null || { echo "Docker não instalado." >&2; exit 1; }
cp -n .env.example .env
python3 - <<'PY'
from pathlib import Path
p=Path('.env');s=p.read_text()
values={
'APP_ENV':'development','PUBLIC_SCHEME':'http','PLATFORM_DOMAIN':'localhost','CONTROL_PLANE_HOST':'control.localhost','API_HOST':'api.localhost','TENANT_DOMAIN_ROOT':'localhost','TRUSTED_HOSTS':'localhost,127.0.0.1,.localhost','CORS_ORIGINS':'http://localhost:8800,http://control.localhost:8800,http://demo.localhost:8800','GATEWAY_BIND_IP':'0.0.0.0','GATEWAY_PORT':'8800','PROVISIONING_ASYNC':'false','BOOTSTRAP_DEMO_TENANT':'true','ALLOW_DEV_TENANT_HEADER':'true'}
lines=[]
for line in s.splitlines():
    key=line.split('=',1)[0] if '=' in line else ''
    lines.append(f'{key}={values[key]}' if key in values else line)
p.write_text('\n'.join(lines)+'\n')
PY
python3 scripts/generate_secrets.py --env .env
docker compose config --quiet
docker compose up -d --build
echo "Control Plane: http://control.localhost:8800"
echo "Tenant demo:   http://demo.localhost:8800"
echo "Credenciais:   $ROOT_DIR/.bootstrap-credentials.txt"
