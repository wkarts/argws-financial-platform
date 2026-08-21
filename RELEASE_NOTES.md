# Release Notes — v1.0.0-rc.5

Esta release consolida o deploy **Dockge image-only** e corrige a persistência para que os dados fiquem diretamente visíveis dentro da pasta da stack em `./data-*`.

## Dockge image-only

A stack `deployments/dockge/compose.yaml` utiliza exclusivamente imagens publicadas:

```text
ghcr.io/wkarts/argws-financial-api:latest
ghcr.io/wkarts/argws-financial-web:latest
ghcr.io/wkarts/argws-financial-gateway:latest
```

O deploy Dockge não depende de:

- `backend/`;
- `frontend/`;
- Dockerfiles;
- `infrastructure/nginx/`;
- build local da aplicação.

`APP_PULL_POLICY=always` mantém o runtime no canal `latest`.

## Persistência visível em `./data-*`

Com `FINANCIAL_DATA_ROOT=.`, a pasta da stack passa a concentrar toda a persistência principal:

```text
argws-financial-platform/
├── compose.yaml
├── .env
├── data-postgres/
├── data-redis/
├── data-rabbitmq/
├── data-minio/
├── data-backups/
├── data-runtime/
└── data-celery/
```

Mapeamentos:

```text
./data-postgres   -> /var/lib/postgresql/data
./data-redis      -> /data
./data-rabbitmq   -> /var/lib/rabbitmq
./data-minio      -> /data
./data-backups    -> /data/backups
./data-runtime    -> /data/runtime
./data-celery     -> /var/lib/celery
```

A stack Dockge não usa volumes Docker nomeados para esses dados. Isso simplifica auditoria, backup físico, migração e restauração da pasta completa da stack.

## Atualização e rollback

- `deployments/dockge/install.sh` força imagens GHCR `latest` e `FINANCIAL_DATA_ROOT=.`;
- `deployments/dockge/update.sh` preserva os diretórios `data-*`, realiza backup e usa `docker compose pull`;
- `deployments/dockge/rollback.sh <versão>` troca temporariamente API, Web e Gateway para aliases imutáveis da release;
- `deployments/dockge/healthcheck.sh` valida a stack image-only.

## Validação contra regressão

Foi adicionado `scripts/validate_dockge_runtime.py`, executado pela CI. A validação falha se:

- algum serviço Dockge voltar a possuir `build:`;
- o Compose voltar a depender de Dockerfiles/código-fonte;
- forem reintroduzidos volumes Docker nomeados;
- faltar algum bind mount `data-*` obrigatório;
- `FINANCIAL_DATA_ROOT` deixar de ser `.` no ambiente padrão Dockge;
- API, Web ou Gateway deixarem de usar as imagens GHCR `:latest`.

## Versionamento e publicação

`VERSION` continua sendo a única fonte canônica da versão da aplicação. Esta correção é preparada como `v1.0.0-rc.5` e segue o fluxo branch → Pull Request → CI → merge → Release.

A publicação continua gerando:

- imagens GHCR `api`, `web`, `gateway`, `acme` e `cloudpanel-agent`;
- ZIP, TAR.ZST e TAR.GZ;
- checksums SHA-256;
- relatório/inventário do pacote;
- artefatos do GitHub Actions;
- GitHub Release normal e Latest.

## CloudPanel / Cloudflare

O CloudPanel permanece externo à stack e deve encaminhar o domínio para:

```text
http://127.0.0.1:GATEWAY_PORT
```

preservando o cabeçalho `Host`. O mesmo gateway atende domínio principal, Control Plane, API e wildcard dos tenants.

## Segurança operacional

Não exclua os diretórios `data-*` durante atualização/redeploy. Credenciais bancárias, Cloudflare, SMTP, Evolution API, MinIO, PostgreSQL e usuários administrativos continuam sendo configuração externa e devem ser rotacionadas quando expostas.
