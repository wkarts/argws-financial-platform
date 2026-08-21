# Deploy no Dockge

A stack Dockge é **image-only**: ela consome exclusivamente as imagens publicadas no GHCR e não precisa compilar backend/frontend no servidor.

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

O `compose.yaml` deve ser o arquivo `deployments/dockge/compose.yaml` desta distribuição. O instalador copia esse arquivo para a raiz da stack para que `./data-*` seja resolvido exatamente no diretório gerenciado pelo Dockge.

Não são necessários na pasta da stack para executar os containers:

- `backend/`;
- `frontend/`;
- Dockerfiles;
- `infrastructure/nginx/`;
- código-fonte da aplicação.

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

Isso permite auditar, copiar, migrar e incluir a pasta inteira da stack em rotinas de backup sem depender de `/var/lib/docker/volumes`.

Se quiser mover todo o conjunto para outro diretório-base, altere `FINANCIAL_DATA_ROOT`; o padrão Dockge é `.`.

## Primeira instalação

1. Copie `deployments/dockge/compose.yaml` para `compose.yaml` na raiz da stack do Dockge.
2. Copie `deployments/dockge/.env.example` para `.env`.
3. Ajuste domínio, porta e segredos.
4. Mantenha `FINANCIAL_DATA_ROOT=.` para usar `./data-*`.
5. Valide com `docker compose config`.
6. Execute `docker compose pull`.
7. Execute `docker compose up -d`.

O Dockge não deve executar `docker compose build` para esta stack.

## Reverse proxy

O gateway publica somente em loopback:

```text
127.0.0.1:${GATEWAY_PORT}
```

O CloudPanel deve criar um reverse proxy para esse endereço e preservar o cabeçalho `Host`. O mesmo gateway atende plataforma, Control Plane, API e tenants por hostname.

Exemplo para `financeiro.exemplo.com.br`:

```text
financeiro.exemplo.com.br
control.financeiro.exemplo.com.br
api.financeiro.exemplo.com.br
*.financeiro.exemplo.com.br
            ↓
http://127.0.0.1:8800
```

## Atualização

`deployments/dockge/update.sh` reaplica o Compose image-only na raiz, preserva os diretórios `data-*`, executa backup, `docker compose pull` e recria os containers usando `:latest`.

## Rollback

```bash
./deployments/dockge/rollback.sh 1.0.0-rc.3
```

O rollback troca temporariamente API, Web e Gateway para os aliases imutáveis daquela release sem alterar os diretórios persistentes. Depois, `update.sh` volta ao canal `latest`.

## Health check

```bash
./deployments/dockge/healthcheck.sh
```
