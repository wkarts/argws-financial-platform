# Release Notes — v1.0.0-rc.13

Esta release corrige ruídos e lacunas observados no runtime real da **ARGWS Financial Platform**, sem alterar a arquitetura, remover serviços ou expor novas portas.

## ACME / Cloudflare

- o container ACME deixa de herdar `LOG_LEVEL=INFO` como nível interno do `acme.sh`;
- `ACME_LOG_LEVEL` passa a ser normalizado para valor numérico, com padrão `1`;
- elimina o erro repetitivo `sh: INFO: out of range` sem modificar o `LOG_LEVEL=INFO` utilizado pela aplicação Python;
- emissão, instalação e renovação DNS-01 continuam preservadas.

## Grafana / Prometheus

- `financial-monitoring-init` passa a criar a árvore completa esperada pelo Grafana 12:
  - `datasources`;
  - `dashboards`;
  - `plugins`;
  - `alerting`;
- elimina os erros de provisionamento causados por diretórios inexistentes;
- o datasource Prometheus existente continua sendo provisionado automaticamente;
- o suporte ao hostname interno `financial-api`, introduzido na rc.12, permanece ativo e também passa a constar nos `.env.example` de Dockge e CloudPanel.

## Runtime CloudPanel / Dockge

- Dockge e CloudPanel continuam byte a byte no mesmo runtime;
- corrigido um caminho residual inválido `/data-certs` no `financial-storage-init`;
- a CI agora impede regressão da árvore de provisionamento do Grafana e da normalização do nível de log do ACME;
- somente `financial-gateway` publica porta no host;
- PostgreSQL, Redis, RabbitMQ, MinIO, Prometheus e Grafana permanecem restritos à rede Docker da stack.

## Redis

O Redis continua sem porta publicada no host. A autenticação interna não foi alterada nesta release para evitar uma troca coordenada de credenciais/URLs durante a estabilização do ambiente já operacional. Essa alteração deve ser tratada separadamente, com atualização simultânea de `REDIS_URL`, Celery result backend e healthchecks.

## Topologia preservada

- `finance.argws.com.br` — landing pública;
- `demo.finance.argws.com.br` — demonstração;
- `control.finance.argws.com.br` — Control Plane;
- `admin.finance.argws.com.br` — alias administrativo;
- `api.finance.argws.com.br` — API;
- `*.finance.argws.com.br` — tenants;
- produção continua image-only via GHCR `:latest`;
- build local permanece separado do deployment de produção.
