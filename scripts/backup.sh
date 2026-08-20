#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
[[ -f .env ]] || { echo "ERRO: .env não encontrado." >&2; exit 1; }
docker compose run --rm financial-api python -m app.cli backup
