#!/usr/bin/env sh
set -eu

# O .env da plataforma usa LOG_LEVEL=INFO para a aplicação. O acme.sh também
# interpreta LOG_LEVEL, porém espera um nível numérico. Removemos apenas desta
# imagem para evitar "sh: INFO: out of range" sem alterar o logging da plataforma.
unset LOG_LEVEL || true

case "${CF_Token:-}" in
  ""|CHANGE_ME*|__CONFIGURE_*)
    echo "CLOUDFLARE_API_TOKEN/CF_Token precisa ser configurado para o perfil ACME." >&2
    exit 64
    ;;
esac

DOMAIN="${ACME_DOMAIN:-}"
EMAIL="${ACME_EMAIL:-}"
STAGING="${ACME_STAGING:-false}"
DNS_SLEEP="${ACME_DNS_SLEEP:-20}"
CHECK_INTERVAL="${ACME_CHECK_INTERVAL_SECONDS:-43200}"
SERVER="letsencrypt"

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
  echo "ACME_DOMAIN e ACME_EMAIL são obrigatórios." >&2
  exit 65
fi

if [ "$STAGING" = "true" ]; then
  SERVER="letsencrypt_test"
fi

mkdir -p /certs

acme.sh --set-default-ca --server "$SERVER"
acme.sh --register-account -m "$EMAIL" --server "$SERVER" || true

issue_certificate() {
  acme.sh --issue \
    --dns dns_cf \
    -d "$DOMAIN" \
    -d "*.$DOMAIN" \
    --dnssleep "$DNS_SLEEP" \
    --server "$SERVER" || true
}

install_bundle() {
  acme.sh --install-cert -d "$DOMAIN" \
    --cert-file /certs/cert.pem \
    --key-file /certs/privkey.pem \
    --ca-file /certs/ca.pem \
    --fullchain-file /certs/fullchain.pem \
    --reloadcmd "date -Iseconds > /certs/last-installed-at.txt"
}

if [ ! -s "/acme.sh/$DOMAIN/fullchain.cer" ]; then
  issue_certificate
fi
install_bundle || {
  issue_certificate
  install_bundle
}

while :; do
  sleep "$CHECK_INTERVAL"
  acme.sh --cron --home /acme.sh --server "$SERVER" || true
  install_bundle || true
done
