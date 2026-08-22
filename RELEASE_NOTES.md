# Release Notes — v1.0.0-rc.9

Esta release restaura e padroniza a infraestrutura completa da **ARGWS Financial Platform**, sem alterar o nome oficial da plataforma.

## Domínio canônico

- `finance.argws.com.br` — landing page pública;
- `demo.finance.argws.com.br` — ambiente demonstrativo;
- `control.finance.argws.com.br` — Control Plane;
- `admin.finance.argws.com.br` — alias administrativo;
- `api.finance.argws.com.br` — API;
- `*.finance.argws.com.br` — tenants provisionados.

## Landing pública

O gateway passa a servir uma landing page própria quando o Host é o domínio base da plataforma. Control Plane, alias admin, demo e tenants continuam usando o frontend autenticado.

## Paridade entre deployments

Docker image-only, Production, Dockge, CloudPanel e Portainer passam a manter o mesmo conjunto funcional, incluindo PostgreSQL, Redis, RabbitMQ, MinIO, workers Celery, backups, ACME/CloudPanel, Prometheus e Grafana.

## Observabilidade restaurada

Prometheus e Grafana voltam ao runtime de produção e permanecem exclusivamente na rede interna Docker. Nenhuma porta de observabilidade é publicada no host.

## Única porta pública

Somente `financial-gateway` possui `ports:`. PostgreSQL, Redis, RabbitMQ, MinIO, Prometheus, Grafana, API e workers ficam privados na stack.

## Build local isolado

Nenhum arquivo em `deployments/` executa build local. O único modelo autorizado para build é `compose.local-build.yaml`, destinado a desenvolvimento e CI.

## Persistência

O bundle Dockge inclui também `data-prometheus`, `data-grafana` e `data-monitoring`.

## Proteção contra regressão

A CI valida paridade de serviços, ausência de build nos runtimes, GHCR `:latest`, única porta publicada, presença de Prometheus/Grafana internos, branding `ARGWS Financial Platform`, domínio padrão `finance.argws.com.br` e a topologia landing/demo/control/admin/api/wildcard.
