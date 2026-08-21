#!/usr/bin/env bash
set -euo pipefail

HOST_ROOT="${HOST_ROOT:-/host}"
CERT_DIR="${CERT_DIR:-/certs}"
STATE_DIR="${STATE_DIR:-/state}"
SITE_DOMAIN="${CLOUDPANEL_SITE_DOMAIN:?CLOUDPANEL_SITE_DOMAIN obrigatório}"
WILDCARD_DOMAIN="${CLOUDPANEL_WILDCARD_DOMAIN:-*.$SITE_DOMAIN}"
SYNC_INTERVAL="${CLOUDPANEL_SYNC_INTERVAL_SECONDS:-60}"
HOST_TMP_REL="/run/argws-financial-cloudpanel-agent"
HOST_TMP="$HOST_ROOT$HOST_TMP_REL"
STATE_FILE="$STATE_DIR/installed.sha256"

log() { printf '%s [financial-cloudpanel-agent] %s\n' "$(date -Iseconds)" "$*"; }
host_exec() { chroot "$HOST_ROOT" /usr/bin/env PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin "$@"; }
host_ready() {
  [[ -d "$HOST_ROOT/etc/nginx/sites-enabled" ]] || return 1
  host_exec /bin/sh -lc 'command -v clpctl >/dev/null 2>&1 && command -v nginx >/dev/null 2>&1'
}
find_vhost() {
  local exact="$HOST_ROOT/etc/nginx/sites-enabled/${SITE_DOMAIN}.conf"
  [[ -f "$exact" ]] && { printf '%s\n' "$exact"; return 0; }
  local candidate
  while IFS= read -r candidate; do
    grep -Eq "^[[:space:]]*server_name[[:space:]].*${SITE_DOMAIN//./\.}" "$candidate" && { printf '%s\n' "$candidate"; return 0; }
  done < <(find "$HOST_ROOT/etc/nginx/sites-enabled" -maxdepth 1 -type f -name '*.conf' -print 2>/dev/null | sort)
  return 1
}
reconcile_vhost() {
  local vhost="$1" pre result
  pre="${vhost}.financial-agent.pre"; cp -a "$vhost" "$pre"
  result="$(python3 - "$vhost" "$SITE_DOMAIN" "$WILDCARD_DOMAIN" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); site=sys.argv[2]; wildcard=sys.argv[3]
lines=p.read_text(encoding='utf-8').splitlines(keepends=True); out=[]; matched=False; changed=False
for line in lines:
    stripped=line.strip()
    if stripped.startswith('server_name '):
        tokens=stripped.split(';',1)[0].split()[1:]
        if site in tokens:
            matched=True
            if wildcard not in tokens:
                pos=line.rfind(';'); line=line[:pos].rstrip()+f' {wildcard};'+line[pos+1:]; changed=True
    out.append(line)
if not matched: print('missing')
elif changed: p.write_text(''.join(out),encoding='utf-8'); print('changed')
else: print('ready')
PY
)"
  if [[ "$result" == "missing" ]]; then mv -f "$pre" "$vhost"; return 2; fi
  if [[ "$result" == "changed" ]]; then
    if ! host_exec nginx -t >/dev/null 2>&1; then mv -f "$pre" "$vhost"; log 'nginx -t falhou; vhost revertido'; return 1; fi
    mv -f "$pre" "${vhost}.financial-agent.$(date +%Y%m%d%H%M%S).bak"
    host_exec nginx -s reload >/dev/null 2>&1 || true
    log "VHost reconciliado: $SITE_DOMAIN $WILDCARD_DOMAIN"
  else rm -f "$pre"; fi
}
certificate_ready() { for f in privkey.pem cert.pem ca.pem fullchain.pem; do [[ -s "$CERT_DIR/$f" ]] || return 1; done; }
certificate_hash() { sha256sum "$CERT_DIR/fullchain.pem" "$CERT_DIR/privkey.pem" | sha256sum | awk '{print $1}'; }
install_certificate() {
  local current previous vhost
  current="$(certificate_hash)"; previous="$(cat "$STATE_FILE" 2>/dev/null || true)"
  [[ "$current" == "$previous" ]] && return 0
  mkdir -p "$HOST_TMP"; chmod 0700 "$HOST_TMP"
  cp "$CERT_DIR"/{privkey.pem,cert.pem,ca.pem,fullchain.pem} "$HOST_TMP"/
  chmod 0600 "$HOST_TMP/privkey.pem"; chmod 0644 "$HOST_TMP"/{cert.pem,ca.pem,fullchain.pem}
  host_exec clpctl site:install:certificate --domainName="$SITE_DOMAIN" \
    --privateKey="$HOST_TMP_REL/privkey.pem" --certificate="$HOST_TMP_REL/cert.pem" \
    --certificateChain="$HOST_TMP_REL/ca.pem" || { log 'clpctl recusou o certificado'; rm -f "$HOST_TMP"/*.pem; return 1; }
  vhost="$(find_vhost)" || return 1
  reconcile_vhost "$vhost" || return 1
  host_exec nginx -t >/dev/null 2>&1
  host_exec nginx -s reload >/dev/null 2>&1 || true
  printf '%s\n' "$current" > "$STATE_FILE"; chmod 0600 "$STATE_FILE"
  date -Iseconds > "$CERT_DIR/last-cloudpanel-installed-at.txt"
  rm -f "$HOST_TMP"/*.pem
  log 'Certificado wildcard sincronizado no CloudPanel'
}

mkdir -p "$STATE_DIR"; chmod 0700 "$STATE_DIR"
log "Agente iniciado; domínio principal=$SITE_DOMAIN wildcard=$WILDCARD_DOMAIN"
while :; do
  if ! host_ready; then log 'CloudPanel/clpctl/nginx ainda indisponíveis'; sleep "$SYNC_INTERVAL"; continue; fi
  if ! vhost="$(find_vhost)"; then log "VHost $SITE_DOMAIN ainda não existe"; sleep "$SYNC_INTERVAL"; continue; fi
  reconcile_vhost "$vhost" || { sleep "$SYNC_INTERVAL"; continue; }
  certificate_ready || { log 'Aguardando certificado ACME'; sleep "$SYNC_INTERVAL"; continue; }
  install_certificate || true
  sleep "$SYNC_INTERVAL"
done
