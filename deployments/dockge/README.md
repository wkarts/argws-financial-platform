# Deploy no Dockge

A stack Dockge é **image-only**: ela consome exclusivamente as imagens publicadas no GHCR e não precisa compilar backend/frontend no servidor.

## Pacote recomendado

Nas Releases, use o arquivo dedicado:

```text
ARGWS-Financial-Platform-v<VERSAO>-Dockge.zip
```

Esse pacote já traz `compose.yaml` image-only na raiz da pasta `argws-financial-platform/`, além de `.env.example`, README, manifesto e diretórios `data-*`.

**Não extraia o pacote completo de código-fonte diretamente dentro da pasta da stack esperando que o Dockge use o Compose correto.** O pacote completo mantém o `compose.yaml` de desenvolvimento/build na raiz. Para Dockge, use sempre o bundle `-Dockge.zip` ou copie explicitamente `deployments/dockge/compose.yaml` para `compose.yaml` na raiz da stack.

## Estrutura operacional da stack

Com `FINANCIAL_DATA_ROOT=.`, a persistência fica visível dentro da própria pasta da stack:

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

O `compose.yaml` do Dockge não contém `build:` e não referencia `backend/`, `frontend/` ou Dockerfiles locais.

## Imagens operacionais

```text
ghcr.io/wkarts/argws-financial-api:latest
ghcr.io/wkarts/argws-financial-web:latest
ghcr.io/wkarts/argws-financial-gateway:latest
```

`APP_PULL_POLICY=always` mantém o canal operacional em `latest`. As tags versionadas continuam disponíveis somente para auditoria/rollback.

## Persistência

O Dockge não usa volumes nomeados para os dados principais. Cada serviço grava em um bind mount explícito:

```text
./data-postgres   -> /var/lib/postgresql/data
./data-redis      -> /data
./data-rabbitmq   -> /var/lib/rabbitmq
./data-minio      -> /data
./data-backups    -> /data/backups
./data-runtime    -> /data/runtime
./data-celery     -> /var/lib/celery
```

Se quiser mover todo o conjunto para outro diretório-base, altere `FINANCIAL_DATA_ROOT`; o padrão Dockge é `.`.

## Primeira instalação

1. Extraia o bundle `ARGWS-Financial-Platform-v<VERSAO>-Dockge.zip` no diretório de stacks do Dockge.
2. Renomeie `.env.example` para `.env`.
3. Ajuste domínio, porta e segredos.
4. Mantenha `FINANCIAL_DATA_ROOT=.`.
5. Valide com `docker compose config`.
6. Execute `docker compose pull`.
7. Execute `docker compose up -d`.

O Dockge não deve executar `docker compose build` para esta stack. Se aparecer `[+] Building`, o arquivo `compose.yaml` em uso não é o bundle Dockge correto.

## Reverse proxy

O gateway publica somente em loopback:

```text
127.0.0.1:${GATEWAY_PORT}
```

O CloudPanel deve criar um reverse proxy para esse endereço e preservar o cabeçalho `Host`. O mesmo gateway atende plataforma, Control Plane, API e tenants por hostname.

## Atualização

`deployments/dockge/update.sh` reaplica o Compose image-only na raiz, preserva os diretórios `data-*`, executa backup, `docker compose pull` e recria os containers usando `:latest`.

## Rollback

```bash
./deployments/dockge/rollback.sh 1.0.0-rc.5
```

O rollback troca temporariamente API, Web e Gateway para os aliases imutáveis daquela release sem alterar os diretórios persistentes. Depois, `update.sh` volta ao canal `latest`.

## Health check

```bash
./deployments/dockge/healthcheck.sh
```
