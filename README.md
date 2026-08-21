# ARGWS Financial Platform

**ARGWS Financial Platform** é uma plataforma SaaS financeira multitenant, web/PWA e Docker-first para gestão de cobranças e recebíveis. O projeto foi construído com **Python 3.13, FastAPI, SQLAlchemy 2, PostgreSQL, Redis, RabbitMQ/Celery, Vue 3, TypeScript, Tailwind CSS e MinIO/S3**.

A versão atual da aplicação é definida exclusivamente pelo arquivo [`VERSION`](VERSION). Os scripts de instalação sincronizam esse valor automaticamente em `APP_VERSION`; o Vite injeta o mesmo valor em `VITE_APP_VERSION`. As imagens operacionais do produto usam sempre a tag `:latest`.

## Índice operacional da entrega

Consulte `DELIVERY_INDEX.md` para localizar rapidamente o Control Plane, Tenant Plane, stacks Docker/Dockge/CloudPanel/Portainer, documentação, PR e comandos de instalação. O relatório técnico consolidado está em `docs/release/DELIVERY_REPORT.md`.

## Arquitetura do produto

A aplicação possui dois planos lógicos e de segurança independentes:

```text
Control Plane
├── tenants
├── planos, capacidades e limites
├── usuários da plataforma
├── domínios, DNS e SSL
├── provisionamento
├── configurações e integrações globais
├── consumo e saúde operacional
├── suporte temporário auditado
├── backups, restore e exportação
└── auditoria global

Tenant Plane
├── múltiplas empresas/CNPJs
├── usuários, papéis e restrições por empresa
├── clientes e contatos
├── serviços e contratos
├── recorrência e recebíveis
├── cobrança, boleto, Pix e Pix Automático
├── CNAB, pagamentos e conciliação
├── negociações e links públicos
├── SMTP, Evolution API e régua de cobrança
├── documentos, recibos e fiscal
├── API keys e webhooks
└── relatórios, importações, exportações e auditoria
```

Cada tenant recebe:

- banco PostgreSQL próprio;
- usuário PostgreSQL próprio;
- storage segregado;
- domínio provisionado `<slug>.<TENANT_DOMAIN_ROOT>`;
- um ou mais domínios personalizados;
- configuração, branding e integrações próprios;
- múltiplas empresas emissoras de cobrança.

O hostname é a autoridade para resolução do tenant. Hosts desconhecidos não recebem fallback para outro tenant.

## Tecnologias

### Backend

- Python 3.13;
- FastAPI;
- SQLAlchemy 2 assíncrono;
- Alembic separado para Control Plane e Tenant Plane;
- Pydantic 2;
- PostgreSQL 17;
- Redis;
- RabbitMQ;
- Celery workers e Celery Beat;
- MinIO/S3;
- Outbox transacional;
- JWT, refresh rotativo, RBAC, API keys e webhooks assinados.

### Frontend

- Vue 3;
- TypeScript;
- Vite;
- Pinia;
- Vue Router;
- Tailwind CSS;
- PWA responsiva;
- portal público de pagamento por token.

### Operação

- Docker Compose com build pelo fonte;
- Docker Compose de produção por imagens `:latest`;
- Dockge;
- CloudPanel;
- Portainer;
- Cloudflare/ACME DNS-01 opcional;
- Prometheus e Grafana opcionais;
- GitHub Actions para CI, imagens, artefatos e release.

## Recursos financeiros

- empresas múltiplas por tenant;
- clientes e contatos financeiros múltiplos;
- serviços e contratos;
- recorrência mensal, semanal, quinzenal, bimestral, trimestral, semestral, anual e personalizada;
- contas a receber;
- cobrança, pagamento parcial, baixa e estorno;
- boleto, Pix, boleto híbrido e provider Sandbox;
- adapter Asaas preparado para credenciais reais;
- Pix Automático com mandatos e instruções;
- CNAB 240 e CNAB 400 extensíveis;
- remessas, retornos e eventos;
- importação OFX/CSV;
- conciliação;
- negociações e acordos;
- links públicos de pagamento;
- recibos em PDF;
- NFS-e Sandbox em XML/PDF;
- documentos financeiros imutáveis com SHA-256;
- importação do financeiro legado;
- relatórios e exportações.

## Comunicações

- SMTP em nível de plataforma, tenant ou empresa;
- Evolution API em nível de plataforma, tenant ou empresa;
- envio de texto, links e documentos;
- webhook idempotente da Evolution API;
- régua automática de cobrança;
- templates por canal;
- Outbox, RabbitMQ, retry e histórico de entrega;
- webhooks de saída assinados por tenant.

## Deploys incluídos

```text
deployments/
├── development/
├── staging/
├── production/
├── docker/
├── dockge/
├── cloudpanel/
├── portainer/
└── common/
```

Cada pacote operacional possui ambiente de exemplo, Compose/stack, instalação, atualização, rollback ou procedimento equivalente, health check e documentação.

### Docker genérico

```bash
./deployments/docker/install.sh \
  --domain financeiro.exemplo.com.br \
  --admin-email admin@exemplo.com.br \
  --mode source
```

Modo baseado em imagens `latest` publicadas no GHCR:

```bash
./deployments/docker/install.sh \
  --domain financeiro.exemplo.com.br \
  --admin-email admin@exemplo.com.br \
  --mode images
```

### Dockge

```bash
sudo ./deployments/dockge/install.sh \
  --domain financeiro.exemplo.com.br \
  --admin-email admin@exemplo.com.br \
  --stacks-dir /opt/stacks
```

### CloudPanel

```bash
sudo ./deployments/cloudpanel/install.sh \
  --domain financeiro.exemplo.com.br \
  --admin-email admin@exemplo.com.br \
  --stack-dir /home/financial/htdocs/financeiro.exemplo.com.br/argws-financial-platform
```

### Portainer

```bash
./deployments/portainer/deploy.sh \
  --domain financeiro.exemplo.com.br \
  --admin-email admin@exemplo.com.br \
  --url https://portainer.exemplo.com.br \
  --api-key ptr_xxxxxxxxx \
  --endpoint-id 1
```

Documentação:

- `docs/operations/DEPLOY_DOCKGE.md`;
- `docs/operations/DEPLOY_CLOUDPANEL.md`;
- `docs/operations/DEPLOY_PORTAINER.md`;
- `docs/operations/BACKUP_RESTORE.md`;
- `docs/operations/DOMAINS_SSL.md`.

## Instalação local

Pré-requisitos:

- Docker Engine;
- Docker Compose v2;
- Python 3 para gerar os segredos.

```bash
cp .env.example .env
python3 scripts/generate_secrets.py --env .env
./scripts/install_local.sh
```

URLs padrão:

```text
Control Plane: http://control.localhost:8800
Tenant demo:   http://demo.localhost:8800
API:           http://api.localhost:8800
```

As credenciais iniciais ficam em `.bootstrap-credentials.txt`. Esse arquivo e o `.env` não devem ser versionados.

## Serviços do Compose fonte

```text
financial-storage-init
financial-postgres
financial-redis
financial-rabbitmq
financial-minio
financial-minio-init
financial-migrate
financial-migrate-tenants
financial-bootstrap
financial-api
financial-worker-default
financial-worker-billing
financial-worker-notifications
financial-worker-backups
financial-beat
financial-web
financial-gateway
```

Profiles opcionais:

```text
cloudpanel  -> financial-acme, financial-cloudpanel-agent
monitoring  -> financial-prometheus, financial-grafana
tools       -> financial-api-test, financial-web-test
```

## Comandos de desenvolvimento e validação

```bash
make validate
make test
make compose-config
make up
make health
make backup
make package
```

Ou diretamente:

```bash
python3 scripts/validate_project.py
cd backend && PYTHONPATH=. pytest -q
node scripts/validate_frontend_syntax.mjs
bash -n deployments/dockge/install.sh
```

## Empacotamento da release

```bash
make package
```

O comando gera ZIP, TAR.ZST, TAR.GZ, checksums SHA-256 e relatório JSON em `release-artifacts/`, excluindo segredos, caches, `.git` e dados de runtime.

## Backup e restore

Backup manual:

```bash
./scripts/backup.sh
```

Restore completo:

```bash
./scripts/restore.sh /caminho/argws-financial-backup-AAAAmmddTHHMMSS.tar.zst
```

Destinos suportados:

- local;
- MinIO/S3;
- Google Drive via rclone;
- Dropbox via rclone.

Os pacotes incluem manifest, checksums e criptografia opcional com `age`. O backup deve ser testado na infraestrutura de destino antes da entrada em produção.

## Segurança e isolamento

- banco e credenciais exclusivos por tenant;
- resolução por hostname sem fallback;
- tokens confrontados com o contexto do domínio;
- segredos criptografados/referenciados;
- permissões por papel e empresa;
- API keys armazenadas por hash;
- webhooks assinados;
- auditoria append-only;
- logs sem credenciais;
- rate limit e locks distribuídos;
- documentos com hash e sem sobrescrita silenciosa.

## Homologações externas

O pacote contém providers Sandbox para executar o ciclo de ponta a ponta e um adapter Asaas pronto para configuração. Credenciais bancárias, carteira/convênio, Pix, layouts CNAB específicos, certificado digital, prefeitura/NFS-e, SMTP, Evolution API, Cloudflare, Drive e Dropbox são dependências externas.

Nenhum código-fonte consegue substituir contrato ou homologação do banco/PSP/prefeitura. A release candidate é completa como plataforma e distribuição, mas a ativação jurídica/financeira real depende dessas credenciais e homologações.

## Documentação principal

- `docs/architecture/ARCHITECTURE.md`;
- `docs/architecture/FLOWS.md`;
- `docs/security/TENANT_ISOLATION.md`;
- `docs/product/COMPLETION_MATRIX.md`;
- `docs/financial/COLLECTION_RULES.md`;
- `docs/integrations/BANKING_CNAB.md`;
- `docs/integrations/SMTP_EVOLUTION.md`;
- `docs/API.md`;
- `docs/LEGACY_IMPORT.md`;
- `docs/ACCEPTANCE_CHECKLIST.md`;
- `docs/release/DELIVERY_REPORT.md`.

## Pull Request

- título: `PR_TITLE.md`;
- descrição completa: `PR_DESCRIPTION.md`.
