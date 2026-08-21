# Release Notes — v1.0.0-rc.3

Esta release corrige definitivamente o fluxo de versionamento e publicação da ARGWS Financial Platform, mantendo **uma única fonte de verdade para a versão da aplicação** e separando-a da tag operacional das imagens Docker.

## Versionamento canônico

- `VERSION` passa a ser a única fonte de verdade da versão da aplicação;
- `APP_VERSION` é sincronizada automaticamente a partir de `VERSION` durante bootstrap/deploy;
- `VITE_APP_VERSION` é obtida automaticamente a partir de `VERSION` durante o build Vue/Vite;
- removida a versão duplicada de `frontend/package.json`;
- removidas versões fixas do backend, Dockerfiles, Compose e arquivos `.env.example`;
- os Dockerfiles empacotam `VERSION` para que a aplicação continue conhecendo sua versão real dentro do container.

## Imagens Docker

As stacks de runtime passam a usar sempre:

```text
BACKEND_IMAGE=ghcr.io/wkarts/argws-financial-api:latest
FRONTEND_IMAGE=ghcr.io/wkarts/argws-financial-web:latest
GATEWAY_IMAGE=ghcr.io/wkarts/argws-financial-gateway:latest
ACME_IMAGE=ghcr.io/wkarts/argws-financial-acme:latest
CLOUDPANEL_AGENT_IMAGE=ghcr.io/wkarts/argws-financial-cloudpanel-agent:latest
```

O workflow de publicação também mantém aliases imutáveis com a versão da release para auditoria e rollback, mas **nenhum arquivo operacional depende desses aliases**.

## Publicação

O workflow canônico `Publish Release` executa:

1. leitura da versão em `VERSION`;
2. CI completa reutilizável;
3. build das cinco imagens Docker;
4. push das imagens para o GHCR com `:latest`, versão e SHA;
5. verificação das imagens publicadas;
6. validação e empacotamento da distribuição;
7. upload dos artefatos no GitHub Actions;
8. criação da tag Git;
9. criação do GitHub Release;
10. upload dos artefatos ZIP, TAR.ZST, TAR.GZ, checksums, inventário e relatórios.

O workflow antigo e duplicado de release foi removido.

## Dependabot

- PRs automáticas antigas foram encerradas;
- atualizações passam a ser agrupadas por ecossistema;
- somente uma PR automática pode ficar aberta por ecossistema;
- atualizações major automáticas foram bloqueadas;
- Tailwind CSS 4 permanece bloqueado até existir uma migração intencional do PostCSS/Tailwind.

## Plataforma

A release mantém o conjunto funcional já entregue:

- Control Plane e Tenant Plane;
- isolamento PostgreSQL/storage por tenant;
- múltiplas empresas por tenant;
- domínios provisionados e personalizados;
- clientes, serviços, contratos, recorrência e contas a receber;
- boleto, Pix, Pix Automático, CNAB 240/400 e conciliação;
- SMTP e Evolution API;
- NFS-e/recibos e documentos;
- Outbox, RabbitMQ e Celery;
- auditoria e segurança;
- backup/restore local, S3/MinIO, Google Drive e Dropbox;
- Docker, Dockge, CloudPanel e Portainer;
- Prometheus/Grafana opcionais.

## Condição da release candidate

A release continua exigindo credenciais e homologações reais para bancos/PSPs, CNAB, NFS-e, SMTP, Evolution API, Cloudflare e destinos externos de backup. Providers Sandbox continuam disponíveis para ambientes sem credenciais reais.
