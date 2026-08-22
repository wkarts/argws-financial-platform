# Release Notes — v1.0.0-rc.7

Esta release consolida o runtime da ARGWS Financial Platform em um contrato único: **deploy sempre por imagens GHCR, somente uma porta publicada e validação de configuração antes das migrations**.

## Uma única porta publicada

Somente `financial-gateway` possui `ports:` no runtime:

```text
127.0.0.1:${GATEWAY_PORT}:80
```

PostgreSQL, Redis, RabbitMQ, MinIO, API, workers e demais serviços continuam acessíveis entre containers pela rede `financial-internal`, sem publicação direta no host.

CloudPanel/Nginx/Reverse Proxy deve apontar somente para o gateway.

## Todos os deployments são image-only

O `compose.yaml` da raiz passa a ser o runtime canônico e não contém `build:`. O mesmo arquivo é usado como contrato para:

- Docker image-only;
- Dockge;
- CloudPanel;
- production;
- Portainer.

As imagens da aplicação são fixas em:

```text
ghcr.io/wkarts/argws-financial-api:latest
ghcr.io/wkarts/argws-financial-web:latest
ghcr.io/wkarts/argws-financial-gateway:latest
```

com `pull_policy: always`.

Development e staging também deixam de usar build em seus deployments.

## Build local isolado

O único modelo com `build:` passa a ser:

```text
compose.local-build.yaml
```

Uso explícito:

```bash
docker compose -f compose.yaml -f compose.local-build.yaml up -d --build
```

Esse override existe somente para desenvolvimento local e CI. `deployments/portainer/stack-build.yaml` fica deliberadamente desabilitado para impedir build acidental em servidor.

## Preflight antes de migrations

Foi adicionado `financial-preflight`, executado com `network_mode: none` antes de inicializar os serviços persistentes e antes de `financial-migrate`.

Ele detecta e relata sem imprimir segredos:

- placeholders de produção (`CHANGE_ME`, etc.);
- `POSTGRES_ADMIN_USER` igual a `POSTGRES_USER` com senha diferente;
- senha/configuração RabbitMQ inconsistente;
- credenciais S3/MinIO incompatíveis no MinIO interno;
- `SMTP_SECURITY` inválido;
- SMTP porta 465 sem `ssl`;
- integrações habilitadas sem configuração mínima.

Isso transforma erros que antes apareciam apenas como `financial-migrate exit 1` em falhas explícitas de configuração antes da migration.

## Reparação de `.env`

`scripts/generate_secrets.py` passa a:

- gerar placeholders ainda não configurados;
- sincronizar `POSTGRES_ADMIN_PASSWORD` quando o usuário admin é o mesmo usuário PostgreSQL;
- sincronizar S3 com MinIO interno;
- regenerar URLs RabbitMQ/Celery a partir da senha efetiva;
- corrigir `SMTP_SECURITY=startssl` e alinhar porta 465 com `ssl`;
- preservar segredos reais existentes, a menos que `--force` seja solicitado.

## Persistência e bundle Dockge

Persistência continua dentro da pasta da stack:

```text
./data-postgres
./data-redis
./data-rabbitmq
./data-minio
./data-backups
./data-runtime
./data-celery
./secrets
```

O asset dedicado `ARGWS-Financial-Platform-v1.0.0-rc.7-Dockge.zip` inclui também os arquivos vazios necessários em `secrets/`.

## Logs e auditoria futura

Os containers usam logging Docker com rotação. A arquitetura de auditoria pelo Control Plane foi formalizada sem abrir portas internas e sem entregar o Docker socket bruto à aplicação.

Acesso excepcional a RabbitMQ, MinIO, PostgreSQL ou Redis deve ser temporário via `docker exec`, SSH tunnel, VPN ou agente interno autenticado, e não por portas permanentes.

## CI e proteção contra regressão

A CI passa a validar:

- ausência de `build:` em qualquer deployment;
- existência do build somente em `compose.local-build.yaml`;
- somente `financial-gateway` com host port;
- PostgreSQL/Redis/RabbitMQ/MinIO sem portas publicadas;
- GHCR `:latest` e `pull_policy: always` no runtime;
- igualdade dos arquivos de runtime ao Compose canônico;
- bundle Dockge e preflight;
- backend, frontend, builds Docker e smoke test.

## Atualização

Para runtime normal:

```bash
docker compose pull
docker compose up -d --remove-orphans
```

Não use `--build` em servidor.

## Segurança

Credenciais expostas em logs, chats ou arquivos compartilhados devem ser rotacionadas antes da publicação em produção. A release não inclui segredos reais.
