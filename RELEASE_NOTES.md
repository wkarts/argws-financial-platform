# Release Notes — v1.0.0-rc.4

Esta release corrige o empacotamento e a operação da stack **Dockge**, que anteriormente ainda dependia de build local apesar de a plataforma já publicar imagens oficiais no GHCR.

## Dockge image-only

A stack `deployments/dockge/compose.yaml` agora utiliza exclusivamente imagens publicadas:

```text
ghcr.io/wkarts/argws-financial-api:latest
ghcr.io/wkarts/argws-financial-web:latest
ghcr.io/wkarts/argws-financial-gateway:latest
```

Não é mais necessário manter na pasta da stack:

- `backend/`;
- `frontend/`;
- Dockerfiles;
- `infrastructure/nginx/`;
- código-fonte da aplicação.

A pasta operacional pode conter somente `compose.yaml` e `.env`.

## Atualização e rollback

- `deployments/dockge/install.sh` usa `docker compose pull` + `up -d`, sem `--build`;
- `deployments/dockge/update.sh` volta sempre ao canal operacional `:latest`;
- `deployments/dockge/rollback.sh <versão>` usa temporariamente os aliases imutáveis daquela release;
- `deployments/dockge/healthcheck.sh` referencia explicitamente o Compose image-only.

## Versionamento

`VERSION` continua sendo a única fonte canônica da versão da aplicação. O Compose Dockge não injeta `APP_VERSION`, permitindo que o backend leia a versão empacotada dentro da imagem. O frontend recebe sua versão no build da imagem.

As variáveis de imagem operacionais permanecem em `:latest`; tags versionadas são mantidas apenas para auditoria e rollback.

## CloudPanel / Cloudflare

O CloudPanel permanece externo à stack e deve encaminhar o domínio para:

```text
http://127.0.0.1:GATEWAY_PORT
```

preservando o cabeçalho `Host`. O mesmo gateway atende domínio principal, Control Plane, API e wildcard dos tenants.

## Validação contra regressão

O validador estrutural agora exige que o Compose Dockge:

- tenha o conjunto esperado de serviços image-only;
- não contenha `build:`;
- referencie `GATEWAY_IMAGE`;
- tenha fallback GHCR `latest` para a API;
- não sobrescreva `APP_VERSION`.

## Publicação

A release publica normalmente:

- imagens GHCR `api`, `web`, `gateway`, `acme` e `cloudpanel-agent`;
- ZIP, TAR.ZST e TAR.GZ;
- checksums SHA-256;
- relatório/inventário do pacote;
- artefatos do GitHub Actions;
- GitHub Release normal e Latest.

## Segurança operacional

Credenciais bancárias, Cloudflare, SMTP, Evolution API, MinIO, PostgreSQL e usuários administrativos continuam sendo configuração externa. Segredos de produção não devem ser versionados nem reutilizados após exposição acidental.
