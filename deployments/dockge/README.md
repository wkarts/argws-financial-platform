# Deploy no Dockge

A stack Dockge é **image-only**: ela consome exclusivamente as imagens publicadas no GHCR e não precisa compilar backend/frontend no servidor.

## Arquivos mínimos da stack

```text
argws-financial-platform/
├── compose.yaml
└── .env
```

O `compose.yaml` deve ser o arquivo `deployments/dockge/compose.yaml` desta distribuição.

Não são necessários na pasta da stack:

- `backend/`;
- `frontend/`;
- Dockerfiles;
- `infrastructure/nginx/`;
- código-fonte do projeto.

## Imagens operacionais

```text
ghcr.io/wkarts/argws-financial-api:latest
ghcr.io/wkarts/argws-financial-web:latest
ghcr.io/wkarts/argws-financial-gateway:latest
```

`APP_PULL_POLICY=always` mantém o canal operacional em `latest`. As tags versionadas continuam disponíveis somente para auditoria/rollback.

## Primeira instalação

1. Copie `deployments/dockge/compose.yaml` para a stack do Dockge.
2. Copie `deployments/dockge/.env.example` para `.env`.
3. Ajuste domínio, porta e segredos.
4. Valide com `docker compose config`.
5. Execute `docker compose pull`.
6. Execute `docker compose up -d`.

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

`deployments/dockge/update.sh` executa backup, `docker compose pull` e recria os containers usando `:latest`.

## Rollback

```bash
./deployments/dockge/rollback.sh 1.0.0-rc.3
```

O rollback troca temporariamente API, Web e Gateway para os aliases imutáveis daquela release. Depois, `update.sh` volta ao canal `latest`.

## Health check

```bash
./deployments/dockge/healthcheck.sh
```
