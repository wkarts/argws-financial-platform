#!/usr/bin/env bash
set -Eeuo pipefail
: "${PORTAINER_WEBHOOK_URL:?PORTAINER_WEBHOOK_URL obrigatória}"
curl --fail --silent --show-error -X POST "$PORTAINER_WEBHOOK_URL"
printf 'Webhook de redeploy acionado com sucesso.\n'
