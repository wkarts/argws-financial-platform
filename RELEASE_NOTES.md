# Release Notes — v1.0.0-rc.10

Esta release consolida as correções de compatibilidade do Dockge sobre a infraestrutura restaurada na `rc.9` da **ARGWS Financial Platform**.

## Dockge sem limite de aliases YAML

O pacote `ARGWS-Financial-Platform-v1.0.0-rc.10-Dockge.zip` passa a conter um `compose.yaml` renderizado em YAML plano. Anchors, aliases e merge keys usados no fonte canônico são expandidos durante o empacotamento e não chegam ao editor do Dockge.

Isso elimina o erro:

`Excessive alias count indicates a resource exhaustion attack`

A validação do pacote usa os tokens reais do parser YAML e reabre o ZIP final para confirmar que não restaram aliases estruturais.

## Preflight alinhado ao `.env` do Dockge

O `financial-preflight` do pacote Dockge recebe também `env_file: .env`. Dessa forma, variáveis específicas do perfil CloudPanel/ACME configuradas pelo operador — como `ACME_DOMAIN`, `ACME_EMAIL`, `CLOUDPANEL_SITE_DOMAIN` e `CLOUDPANEL_WILDCARD_DOMAIN` — ficam disponíveis ao preflight sem duplicação manual no Compose.

As variáveis declaradas explicitamente em `environment` continuam tendo precedência sobre `env_file`.

## Infraestrutura preservada

A correção não remove recursos da stack:

- 24 serviços permanecem no runtime;
- PostgreSQL, Redis, RabbitMQ, MinIO, Prometheus e Grafana continuam internos à rede Docker;
- Prometheus e Grafana permanecem presentes no runtime de produção;
- ACME e CloudPanel Agent permanecem no perfil `cloudpanel`;
- somente `financial-gateway` publica porta no host;
- deployments continuam image-only via GHCR;
- build local continua isolado em `compose.local-build.yaml` para desenvolvimento/CI.

## Domínios canônicos

- `finance.argws.com.br` — landing pública;
- `demo.finance.argws.com.br` — demonstração;
- `control.finance.argws.com.br` — Control Plane;
- `admin.finance.argws.com.br` — alias administrativo;
- `api.finance.argws.com.br` — API;
- `*.finance.argws.com.br` — tenants.

## Segurança e persistência

Apenas o gateway permanece acessível pelo host. Os dados continuam em diretórios `./data-*`, incluindo PostgreSQL, Redis, RabbitMQ, MinIO, Celery, backups, Prometheus, Grafana, monitoramento, ACME, certificados e estado do agente CloudPanel.
