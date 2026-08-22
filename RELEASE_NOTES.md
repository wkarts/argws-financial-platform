# Release Notes — v1.0.0-rc.13

Esta release corrige de forma localizada os pontos observados no runtime de produção da **ARGWS Financial Platform**, preservando a arquitetura image-only, os nomes públicos e a topologia atual.

## Observabilidade

- o runtime Dockge/CloudPanel passa a criar explicitamente os diretórios de provisionamento `datasources`, `dashboards`, `plugins` e `alerting` antes de iniciar o Grafana;
- elimina os erros de diretório inexistente em `/etc/grafana/provisioning/*` sem remover o provisionamento automático do Prometheus;
- mantém Prometheus e Grafana somente na rede interna da stack, sem novas portas publicadas;
- republica a imagem da API contendo a aceitação explícita do hostname interno `financial-api`, necessária para o scrape de `/metrics` sem HTTP 400.

## ACME / CloudPanel

- o container ACME deixa de herdar `LOG_LEVEL=INFO` da aplicação antes de executar `acme.sh`;
- elimina o ruído `sh: INFO: out of range` sem alterar `LOG_LEVEL` dos demais componentes;
- emissão, renovação e instalação do certificado `finance.argws.com.br` + `*.finance.argws.com.br` permanecem preservadas;
- o `financial-cloudpanel-agent` continua responsável por garantir Reverse Proxy, wildcard e instalação do certificado no host.

## Runtime preservado

- `ARGWS Financial Platform` permanece como nome oficial;
- `finance.argws.com.br` — landing pública;
- `demo.finance.argws.com.br` — demonstração;
- `control.finance.argws.com.br` — Control Plane;
- `admin.finance.argws.com.br` — alias administrativo;
- `api.finance.argws.com.br` — API;
- `*.finance.argws.com.br` — tenants;
- somente `financial-gateway` publica porta no host;
- PostgreSQL, Redis, RabbitMQ, MinIO, Prometheus e Grafana permanecem internos;
- produção continua exclusivamente por imagens GHCR `:latest`;
- build local permanece fora dos manifests de produção.

## Nota sobre Redis

O Redis continua sem porta publicada no host e restrito à rede Docker interna, conforme o contrato de segurança da plataforma. O aviso nativo do Redis sobre ausência de autenticação não representa exposição externa neste runtime; autenticação Redis será tratada como endurecimento separado para evitar uma rotação abrupta de credenciais em instalações já persistidas.
