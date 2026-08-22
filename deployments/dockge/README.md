# ARGWS Financial Platform — Dockge / CloudPanel

Runtime de produção **image-only**. O servidor não compila backend, frontend ou gateway.

## Domínios padrão

- Landing: `https://finance.argws.com.br`
- Demonstração: `https://demo.finance.argws.com.br`
- Control Plane: `https://control.finance.argws.com.br`
- Alias administrativo: `https://admin.finance.argws.com.br`
- API: `https://api.finance.argws.com.br`
- Tenants: `https://<slug-ou-hash>.finance.argws.com.br`

O Cloudflare usa `*.finance.argws.com.br`; o CloudPanel precisa de apenas um Reverse Proxy para `finance.argws.com.br -> http://127.0.0.1:GATEWAY_PORT`.

## Rede

Somente `financial-gateway` publica porta no host. PostgreSQL, Redis, RabbitMQ, MinIO, Prometheus, Grafana, API e workers ficam na rede `financial-internal`.

## Observabilidade

Prometheus e Grafana fazem parte da stack e permanecem internos. Acesso operacional excepcional deve ocorrer por túnel/VPN ou, futuramente, pelo Control Plane — nunca por portas administrativas permanentemente publicadas.

## Persistência

Os dados ficam ao lado da stack em `data-postgres`, `data-redis`, `data-rabbitmq`, `data-minio`, `data-backups`, `data-runtime`, `data-celery`, `data-prometheus`, `data-grafana`, `data-monitoring`, `data-acme`, `data-certs`, `data-cloudpanel-agent` e `secrets`.

## Instalação

```bash
cp .env.example .env
python3 scripts/generate_secrets.py --env .env
docker compose config
docker compose pull
docker compose up -d --remove-orphans
```

Para build local use somente o modelo de desenvolvimento:

```bash
docker compose -f compose.yaml -f compose.local-build.yaml up -d --build
```

Esse comando não deve ser usado no servidor Dockge/CloudPanel.
