# ARGWS Financial Platform

Plataforma SaaS financeira multitenant para cobrança e gestão de recebíveis, construída com **Python 3.13, FastAPI, PostgreSQL, Redis, RabbitMQ/Celery, Vue 3, Tailwind CSS, PWA, MinIO/S3 e Docker Compose**.

O produto possui dois planos lógicos independentes:

- **Control Plane:** governa tenants, provisionamento, domínios, bancos isolados, storage, planos, saúde e backups.
- **Tenant Plane:** opera empresas, usuários, clientes, contratos, recorrências, recebíveis, cobranças, pagamentos, CNAB, conciliação, SMTP, Evolution API, recibos, documentos fiscais e auditoria.

Cada tenant recebe um **banco PostgreSQL próprio**, um bucket MinIO/S3 próprio e pelo menos um domínio provisionado no formato:

```text
<slug>.financeiro.exemplo.com.br
```

Cada tenant pode controlar várias empresas/CNPJs e limitar usuários por empresa.

## Recursos implementados

- Control Plane com autenticação separada;
- provisionamento idempotente de tenant;
- banco PostgreSQL e usuário exclusivos por tenant;
- domínio provisionado e domínios personalizados;
- resolução de tenant por hostname, sem fallback entre tenants;
- cache seguro de resolução no Redis;
- empresas, clientes, serviços e contratos;
- recorrência e geração idempotente de recebíveis;
- cobrança por provider bancário;
- provider bancário Sandbox totalmente funcional;
- geração de boleto/PIX Sandbox com documento PDF;
- pagamentos manuais e via webhook;
- CNAB 240 extensível, remessa e parser de retorno;
- contas bancárias e convênios;
- conciliação manual e automática;
- SMTP e Evolution API por plataforma, tenant ou empresa;
- régua automática D-7/D-1/D0/D+1/D+5, templates editáveis e contatos financeiros múltiplos;
- Outbox transacional, Celery, RabbitMQ, retry e filas separadas;
- recibos em PDF;
- provider NFS-e Sandbox com XML e PDF;
- documentos imutáveis no MinIO/S3 com SHA-256;
- importador do padrão `FINANCEIRO Vitor.zip` com prévia e deduplicação;
- usuários, RBAC, papéis prontos e restrição por empresa;
- auditoria operacional e financeira;
- backup de Control Plane, todos os bancos dos tenants e MinIO/S3;
- upload de backup para S3, Google Drive e Dropbox via rclone;
- restauração completa com checksum e modo de manutenção;
- frontend responsivo/PWA para Control Plane e Tenant Plane;
- Docker Compose, CloudPanel, Dockge, CI e release automation.

## Limites de homologação externa

O núcleo é operacional e contém providers Sandbox para executar o fluxo completo sem banco ou prefeitura. Integrações bancárias reais, layouts CNAB específicos e NFS-e municipal exigem credenciais, contratos e homologação de cada instituição. Esses pontos foram isolados por interfaces para não alterar o domínio financeiro.

O CNAB 240 fornecido garante estrutura de registros com 240 posições e extensão por banco; ele **não deve ser enviado em produção antes da homologação do banco e da carteira contratada**. A infraestrutura para CNAB 400 está prevista no boundary de providers, mas cada layout precisa ser implementado conforme o banco escolhido.

## Início rápido local

Pré-requisitos:

- Docker Engine;
- Docker Compose v2;
- Python 3 apenas para geração inicial dos segredos.

```bash
cp .env.example .env
python3 scripts/generate_secrets.py --env .env
./scripts/install_local.sh
```

A instalação local configura:

```text
Control Plane: http://control.localhost:8800
Tenant demo:   http://demo.localhost:8800
```

As credenciais geradas ficam em:

```text
.bootstrap-credentials.txt
```

Esse arquivo contém segredos e não deve ser versionado.

## Deploy CloudPanel + Dockge

Exemplo para o domínio-base `financeiro.exemplo.com.br`:

```bash
./scripts/deploy_cloudpanel_dockge.sh \
  --domain financeiro.exemplo.com.br \
  --cloudflare-zone exemplo.com.br \
  --admin-email admin@exemplo.com.br \
  --stack-dir /home/usuario/htdocs/financeiro.exemplo.com.br/dockge-stacks/argws-financial-platform
```

O instalador:

1. copia a stack para o diretório do Dockge;
2. gera `.env` e segredos fortes;
3. configura domínios;
4. valida o projeto e o Compose;
5. constrói as imagens;
6. aplica migrations do Control Plane;
7. cria o administrador inicial;
8. sobe todos os serviços;
9. aguarda `/health/ready`;
10. mostra URLs e credenciais.

Documentação completa: `docs/operations/DEPLOY_CLOUDPANEL_DOCKGE.md`.

## DNS esperado

```text
financeiro.exemplo.com.br             -> servidor/CloudPanel
control.financeiro.exemplo.com.br     -> servidor/CloudPanel
api.financeiro.exemplo.com.br         -> saúde, OpenAPI e informações públicas da API
*.financeiro.exemplo.com.br           -> servidor/CloudPanel
```

As operações financeiras, integrações e webhooks usam sempre o domínio provisionado/customizado do tenant. O hostname seleciona o banco PostgreSQL exclusivo; o host central `api.*` não é um atalho para atravessar esse isolamento.

Domínios personalizados, como `cobranca.cliente.com.br`, são reconciliados pelo Domain Agent documentado em `docs/operations/DOMAINS_SSL.md`.

## Serviços Docker

```text
financial-postgres
financial-redis
financial-rabbitmq
financial-minio
financial-minio-init
financial-migrate
financial-init
financial-api
financial-worker
financial-beat
financial-web
financial-gateway
```

Serviços de teste no profile `tools`:

```text
financial-api-test
financial-web-test
```

## Comandos operacionais

```bash
# Validar estrutura
python3 scripts/validate_project.py

# Validar Compose
docker compose config --quiet

# Subir/reconstruir
docker compose up -d --build

# Estado
docker compose ps

# Logs
docker compose logs -f --tail=200 financial-api financial-worker financial-beat

# Testes em containers
docker compose --profile tools run --rm financial-api-test
docker compose --profile tools run --rm financial-web-test

# Backup imediato
./scripts/backup.sh

# Restore completo
./scripts/restore.sh /caminho/argws-financial-backup-AAAAmmddTHHMMSS.tar.zst
```

## URLs de observabilidade

```text
/health
/health/live
/health/ready
/metrics
/api/docs
/api/redoc
```

## Estrutura

```text
backend/
  app/
    api/
    core/
    db/
    models/
    providers/
    services/
    workers/
  migrations/
  tests/
frontend/
  src/
infrastructure/
deployments/
scripts/
docs/
compose.yaml
```

## Documentos principais

- `docs/architecture/ARCHITECTURE.md`
- `docs/architecture/FLOWS.md`
- `docs/security/TENANT_ISOLATION.md`
- `docs/operations/DEPLOY_CLOUDPANEL_DOCKGE.md`
- `docs/operations/DOMAINS_SSL.md`
- `docs/operations/BACKUP_RESTORE.md`
- `docs/integrations/SMTP_EVOLUTION.md`
- `docs/financial/COLLECTION_RULES.md`
- `docs/integrations/BANKING_CNAB.md`
- `docs/LEGACY_IMPORT.md`
- `docs/API.md`
- `docs/ACCEPTANCE_CHECKLIST.md`

## Versão

```text
0.1.0-alpha.1
```

A versão Alpha entrega a plataforma executável e o fluxo completo em Sandbox. A classificação Alpha permanece enquanto adapters bancários e fiscais reais não forem homologados para uma instituição específica.
