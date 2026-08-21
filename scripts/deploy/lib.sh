#!/usr/bin/env bash
set -Eeuo pipefail

log() { printf '\033[1;36m[%s]\033[0m %s\n' "$(date '+%H:%M:%S')" "$*"; }
warn() { printf '\033[1;33m[AVISO]\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31m[ERRO]\033[0m %s\n' "$*" >&2; exit 1; }
require_cmd() { command -v "$1" >/dev/null 2>&1 || die "Comando obrigatório ausente: $1"; }

set_env() {
  local file="$1" key="$2" value="$3"
  python3 - "$file" "$key" "$value" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); key=sys.argv[2]; value=sys.argv[3]
lines=p.read_text(encoding='utf-8').splitlines() if p.exists() else []
out=[]; found=False
for line in lines:
    if line.startswith(key+'='):
        out.append(f'{key}={value}'); found=True
    else:
        out.append(line)
if not found:
    out.append(f'{key}={value}')
p.write_text('\n'.join(out)+'\n',encoding='utf-8')
PY
}

get_env() {
  local file="$1" key="$2"
  awk -F= -v k="$key" '$1==k {sub($1 FS,""); print; exit}' "$file"
}

sync_project() {
  local root="$1" target="$2"
  mkdir -p "$target"
  if [[ "$(realpath "$root")" == "$(realpath "$target")" ]]; then return 0; fi
  tar --exclude='.git' --exclude='.env' --exclude='.bootstrap-credentials.txt' \
      --exclude='financial-data' --exclude='node_modules' --exclude='dist' \
      --exclude='__pycache__' --exclude='.pytest_cache' --exclude='.releases' \
      -C "$root" -cf - . | tar -C "$target" -xf -
}

compose_profiles() {
  local env_file="$1" profiles=()
  [[ "$(get_env "$env_file" ACME_ENABLED || true)" == "true" ]] && profiles+=(cloudpanel)
  [[ "$(get_env "$env_file" CLOUDPANEL_AGENT_ENABLED || true)" == "true" ]] && profiles+=(cloudpanel)
  [[ "$(get_env "$env_file" MONITORING_ENABLED || true)" == "true" ]] && profiles+=(monitoring)
  if ((${#profiles[@]})); then local IFS=,; printf '%s' "${profiles[*]}"; fi
}

compose_cmd() {
  local env_file="$1"; shift
  local compose_file="${COMPOSE_FILE_PATH:-compose.yaml}" profiles
  profiles="$(compose_profiles "$env_file")"
  if [[ -n "$profiles" ]]; then
    COMPOSE_PROFILES="$profiles" docker compose --env-file "$env_file" -f "$compose_file" "$@"
  else
    docker compose --env-file "$env_file" -f "$compose_file" "$@"
  fi
}

wait_ready() {
  local port="$1" attempts="${2:-120}" sleep_seconds="${3:-2}" i
  for ((i=1;i<=attempts;i++)); do
    if curl -fsS "http://127.0.0.1:${port}/health/ready" >/dev/null 2>&1; then
      log "Readiness confirmado em 127.0.0.1:${port}"
      return 0
    fi
    sleep "$sleep_seconds"
  done
  return 1
}

ensure_runtime_files() {
  local root="$1" env_file="$2"
  mkdir -p "$root/secrets" "$root/financial-data" "$root/.releases"
  local rclone age
  rclone="$(get_env "$env_file" RCLONE_CONFIG_PATH || true)"
  age="$(get_env "$env_file" BACKUP_AGE_IDENTITY_PATH || true)"
  if [[ -n "$rclone" && "$rclone" != /* ]]; then rclone="$root/${rclone#./}"; fi
  if [[ -n "$age" && "$age" != /* ]]; then age="$root/${age#./}"; fi
  if [[ -n "$rclone" && ! -e "$rclone" ]]; then
    mkdir -p "$(dirname "$rclone")"
    cp "$root/infrastructure/backup/rclone.conf.example" "$rclone"
    chmod 0600 "$rclone"
  fi
  if [[ -n "$age" && ! -e "$age" ]]; then
    mkdir -p "$(dirname "$age")"
    : > "$age"
    chmod 0600 "$age"
  fi
}

prepare_env() {
  local root="$1" env_example="$2" env_file="$3" domain="$4" email="$5"
  [[ -f "$env_file" ]] || cp "$env_example" "$env_file"
  local zone="${domain#*.}"
  set_env "$env_file" PLATFORM_DOMAIN "$domain"
  set_env "$env_file" CONTROL_PLANE_HOST "control.$domain"
  set_env "$env_file" API_HOST "api.$domain"
  set_env "$env_file" TENANT_DOMAIN_ROOT "$domain"
  set_env "$env_file" PLATFORM_ADMIN_EMAIL "$email"
  set_env "$env_file" ACME_EMAIL "$email"
  set_env "$env_file" ACME_DOMAIN "$domain"
  set_env "$env_file" CLOUDFLARE_ZONE_NAME "$zone"
  set_env "$env_file" CLOUDFLARE_TENANT_RECORD_TARGET "$domain"
  set_env "$env_file" SMTP_FROM_EMAIL "financeiro@$zone"
  set_env "$env_file" VITE_CONTROL_PLANE_HOST "control.$domain"
  set_env "$env_file" TRUSTED_HOSTS "$domain,control.$domain,api.$domain,.$domain,localhost,127.0.0.1"
  set_env "$env_file" CORS_ORIGINS "https://$domain,https://control.$domain"
  python3 "$root/scripts/generate_secrets.py" --env "$env_file"
  chmod 0600 "$env_file"
  ensure_runtime_files "$root" "$env_file"
}

validate_project() {
  local root="$1" runtime="${2:-false}"
  if [[ "$runtime" == "true" ]]; then
    python3 "$root/scripts/validate_project.py" --allow-runtime-files
  else
    python3 "$root/scripts/validate_project.py"
  fi
}

backup_before_update() {
  local root="$1" env_file="${2:-.env}"
  cd "$root"
  if compose_cmd "$env_file" ps --status running 2>/dev/null | grep -q financial-api; then
    log "Gerando backup antes da atualização"
    compose_cmd "$env_file" run --rm financial-api python -m app.cli backup
  else
    warn "Stack não está ativa; backup pré-atualização ignorado."
  fi
}
