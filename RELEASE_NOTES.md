# Release Notes — v1.0.0-rc.11

Esta release corrige a etapa de inicialização de domínios da **ARGWS Financial Platform** sem alterar a arquitetura da stack.

## Domain bootstrap não bloqueante

O `financial-domain-init` continua tentando reconciliar automaticamente o wildcard `*.finance.argws.com.br` na Cloudflare, porém falhas externas de DNS/API não derrubam mais a plataforma inteira.

Se a Cloudflare estiver temporariamente indisponível, o token não tiver permissão suficiente ou o domínio base ainda não possuir um registro de origem utilizável, o serviço passa a emitir um relatório JSON com `status: DEGRADED`, `blocking: false` e os detalhes do erro, retornando sucesso para liberar PostgreSQL, Redis, RabbitMQ, MinIO, migrações, API e workers.

A validação de configuração continua sendo feita pelo `financial-preflight`; esta alteração não remove a checagem de secrets, Cloudflare, ACME ou CloudPanel.

## Infraestrutura preservada

- nome oficial: `ARGWS Financial Platform`;
- domínio público: `finance.argws.com.br`;
- demo: `demo.finance.argws.com.br`;
- Control Plane: `control.finance.argws.com.br`;
- API: `api.finance.argws.com.br`;
- tenants: `*.finance.argws.com.br`;
- 24 serviços preservados;
- Prometheus e Grafana continuam internos;
- somente `financial-gateway` publica porta no host;
- produção continua image-only via GHCR;
- Dockge/CloudPanel continuam usando YAML plano, sem anchors/aliases.
