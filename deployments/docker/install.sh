#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; source "$ROOT/scripts/deploy/lib.sh"; cd "$ROOT"
DOMAIN=""; EMAIL=""; MODE=source; SKIP_UP=false
while (($#)); do case "$1" in --domain) DOMAIN="${2,,}";shift 2;; --admin-email) EMAIL="${2,,}";shift 2;; --mode) MODE="$2";shift 2;; --skip-up) SKIP_UP=true;shift;; -h|--help) echo 'Uso: install.sh --domain DOMINIO --admin-email EMAIL [--mode source|images] [--skip-up]';exit 0;; *) die "Opção desconhecida: $1";; esac; done
[[ "$DOMAIN" == *.* ]] || die '--domain inválido'; [[ "$EMAIL" == *@* ]] || die '--admin-email inválido'; [[ "$MODE" =~ ^(source|images)$ ]] || die '--mode deve ser source ou images'
[[ -f .env ]] || cp .env.example .env
prepare_env "$ROOT" "$ROOT/.env.example" "$ROOT/.env" "$DOMAIN" "$EMAIL"
if [[ "$MODE" == images ]]; then COMPOSE_FILE_PATH=deployments/docker/compose.images.yaml; set_env .env APP_PULL_POLICY always; else COMPOSE_FILE_PATH=compose.yaml; set_env .env APP_PULL_POLICY build; fi
export COMPOSE_FILE_PATH
validate_project "$ROOT" true
$SKIP_UP && { log 'Configuração preparada sem subir containers.'; exit 0; }
require_cmd docker; docker compose version >/dev/null || die 'Docker Compose v2 ausente'
compose_cmd .env config --quiet
if [[ "$MODE" == images ]]; then compose_cmd .env pull; compose_cmd .env up -d --remove-orphans; else compose_cmd .env up -d --build --remove-orphans; fi
wait_ready "$(get_env .env GATEWAY_PORT)" || die 'Stack não ficou saudável'
compose_cmd .env ps
