# Release Notes — v1.0.0-rc.14

Esta release corrige o último bloqueio observado no bootstrap real da **ARGWS Financial Platform**, sem alterar a topologia da stack nem remover serviços.

## Bootstrap do tenant demo

O `financial-domain-init` já tratava falhas externas da Cloudflare como `DEGRADED`, porém o bootstrap do tenant demo ainda executava uma segunda reconciliação DNS através do `ProvisioningService`. Quando a Cloudflare respondia `403 Forbidden`, essa segunda chamada encerrava `financial-bootstrap` com exit 1 e impedia API, workers, Prometheus e Grafana de iniciarem.

A rc.14 corrige especificamente esse caminho:

- erros HTTP originados em `api.cloudflare.com` durante o provisionamento automático do tenant demo deixam de derrubar o container `financial-bootstrap`;
- erros `CLOUDFLARE_*` continuam sendo tratados como falha externa não bloqueante para o bootstrap;
- o job de provisionamento e o tenant continuam registrando o erro e permanecem disponíveis para reprocessamento;
- erros de banco, migrations, MinIO/S3, RabbitMQ ou outros componentes continuam fatais e não são mascarados;
- o bootstrap informa explicitamente que o tenant demo ficou pendente de reconciliação externa;
- testes garantem que um `403` da Cloudflare não bloqueie o boot e que erros HTTP de outros serviços continuem sendo propagados.

## Diagnóstico confirmado no ambiente real

O log que motivou esta correção mostrava:

- `financial-preflight`: `PASS`;
- ACME: certificado base + wildcard emitido e instalado com sucesso;
- CloudPanel Agent: VHost/certificado instalados;
- PostgreSQL, Redis, RabbitMQ e MinIO operacionais;
- falha exclusiva em `financial-bootstrap` ao chamar `ensure_managed_wildcard()` e receber `403 Forbidden` da API Cloudflare.

## Topologia preservada

- `finance.argws.com.br` — landing pública;
- `demo.finance.argws.com.br` — demonstração;
- `control.finance.argws.com.br` — Control Plane;
- `admin.finance.argws.com.br` — alias administrativo;
- `api.finance.argws.com.br` — API;
- `*.finance.argws.com.br` — tenants;
- somente `financial-gateway` publica porta no host;
- PostgreSQL, Redis, RabbitMQ, MinIO, Prometheus e Grafana continuam internos;
- produção continua image-only via GHCR `:latest`.
