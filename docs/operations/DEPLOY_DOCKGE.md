# Deploy no Dockge

## Objetivo

Executar a ARGWS Financial Platform no Dockge usando **somente imagens publicadas no GHCR**, sem compilar backend/frontend no servidor e sem exigir o código-fonte dentro da pasta da stack.

## Arquivos

```text
deployments/dockge/
├── .env.example
├── compose.yaml
├── install.sh
├── update.sh
├── rollback.sh
├── healthcheck.sh
└── README.md
```

O `deployments/dockge/compose.yaml` é uma stack **image-only** independente do Compose de desenvolvimento/build da raiz.

## Pré-requisitos

- Linux 64-bit;
- Docker Engine;
- Docker Compose v2;
- Dockge instalado;
- acesso ao diretório de stacks do Dockge;
- acesso ao `ghcr.io`;
- proxy reverso externo para `127.0.0.1:GATEWAY_PORT`.

## Imagens

O canal operacional utiliza sempre `latest`:

```text
ghcr.io/wkarts/argws-financial-api:latest
ghcr.io/wkarts/argws-financial-web:latest
ghcr.io/wkarts/argws-financial-gateway:latest
```

As tags versionadas continuam publicadas para auditoria e rollback, mas não são fixadas no `.env` de operação normal.

## Importação manual no Dockge

Na pasta da stack são suficientes:

```text
argws-financial-platform/
├── compose.yaml
└── .env
```

Use `deployments/dockge/compose.yaml` como `compose.yaml` da stack e `deployments/dockge/.env.example` como base do `.env`.

Depois:

```bash
docker compose config
docker compose pull
docker compose up -d
```

**Não execute `docker compose build`** para a stack Dockge.

## Instalação automatizada

A partir da raiz do pacote completo:

```bash
sudo ./deployments/dockge/install.sh \
  --domain financeiro.exemplo.com.br \
  --admin-email admin@exemplo.com.br \
  --stacks-dir /opt/stacks \
  --stack-name argws-financial-platform
```

O instalador prepara o `.env`, gera os segredos, força `APP_PULL_POLICY=always`, aponta API/Web/Gateway para `ghcr.io/wkarts/...:latest`, executa `docker compose pull`, sobe a stack sem build e aguarda `/health/ready`.

## Reverse proxy

O gateway publica somente em loopback. Exemplo:

```env
GATEWAY_BIND_IP=127.0.0.1
GATEWAY_PORT=18800
```

No CloudPanel, o reverse proxy deve apontar para:

```text
http://127.0.0.1:18800
```

O vhost deve preservar o cabeçalho `Host` e aceitar o domínio principal, Control Plane, API e wildcard de tenants.

## Atualização

```bash
./deployments/dockge/update.sh
```

A atualização realiza backup, volta as imagens ao canal `latest`, executa `docker compose pull`, recria os containers e valida readiness.

## Rollback

```bash
./deployments/dockge/rollback.sh 1.0.0-rc.3
```

O rollback troca temporariamente API, Web e Gateway para os aliases imutáveis da versão informada. Para retornar ao canal operacional `latest`, execute `update.sh`.

## Health check

```bash
./deployments/dockge/healthcheck.sh
```

Ou diretamente:

```bash
docker compose ps
curl -fsS http://127.0.0.1:${GATEWAY_PORT}/health/live
curl -fsS http://127.0.0.1:${GATEWAY_PORT}/health/ready
```

## Persistência

A stack image-only usa volumes Docker nomeados para PostgreSQL, Redis, RabbitMQ, MinIO, backups, runtime e Celery. Não remova os volumes sem backup validado.
