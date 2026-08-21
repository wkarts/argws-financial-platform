# Release Notes — v1.0.0-rc.6

Esta release corrige o último ponto que ainda podia levar o Dockge a tentar fazer build local: a distribuição passa a publicar um **bundle Dockge dedicado**, pronto para extração direta no diretório de stacks.

## Novo asset Dockge

A Release passa a incluir:

```text
ARGWS-Financial-Platform-v1.0.0-rc.6-Dockge.zip
```

Dentro dele existe uma única pasta operacional:

```text
argws-financial-platform/
├── compose.yaml
├── .env.example
├── README.md
├── DOCKGE_PACKAGE.json
├── data-postgres/
├── data-redis/
├── data-rabbitmq/
├── data-minio/
├── data-backups/
├── data-runtime/
└── data-celery/
```

O `compose.yaml` desse bundle é o Compose **image-only** do Dockge. Ele não contém `build:` e não depende de `backend/`, `frontend/` ou Dockerfiles locais.

## Por que esta correção foi necessária

O pacote completo de código-fonte continua contendo o `compose.yaml` da raiz destinado a desenvolvimento/build. Quando esse pacote era extraído diretamente dentro da pasta da stack, o Dockge podia selecionar esse Compose e tentar localizar:

```text
./backend
./frontend
```

O sintoma típico era:

```text
[+] Building ...
could not find .../frontend: no such file or directory
```

A partir desta release, para Dockge o asset correto é explicitamente o arquivo `-Dockge.zip`.

## Imagens operacionais protegidas contra `.env` legado

O Compose Dockge fixa diretamente:

```text
ghcr.io/wkarts/argws-financial-api:latest
ghcr.io/wkarts/argws-financial-web:latest
ghcr.io/wkarts/argws-financial-gateway:latest
```

com `pull_policy: always` no próprio Compose. Assim, valores antigos como `APP_PULL_POLICY=build` ou `BACKEND_IMAGE=argws-financial-api:latest` em um `.env` reaproveitado não conseguem reativar build local nem substituir as imagens oficiais do runtime Dockge.

O `.env.example` continua documentando:

```env
APP_PULL_POLICY=always
FINANCIAL_DATA_ROOT=.
```

As tags versionadas permanecem apenas para auditoria e rollback.

## Persistência

A persistência continua em bind mounts visíveis dentro da própria pasta da stack:

```text
./data-postgres   -> /var/lib/postgresql/data
./data-redis      -> /data
./data-rabbitmq   -> /var/lib/rabbitmq
./data-minio      -> /data
./data-backups    -> /data/backups
./data-runtime    -> /data/runtime
./data-celery     -> /var/lib/celery
```

Nenhum desses dados depende de volumes Docker nomeados na stack Dockge.

## Validação e CI

A CI agora também executa `scripts/package_dockge_stack.py` e valida que o ZIP dedicado é gerado corretamente. `scripts/validate_dockge_runtime.py` verifica ausência de `build:`, bind mounts `data-*`, imagens GHCR `:latest` fixas e `pull_policy: always` fixo.

O workflow de Release só conclui se o bundle Dockge existir e for publicado junto com os demais assets. A verificação pós-release passa a validar nove assets, incluindo o novo ZIP Dockge.

## Política de alterações no repositório

O workflow de prova de Release deixa de escrever diretamente na `main`. Ele apenas valida a Release e publica um artefato de prova no GitHub Actions. Alterações de código, configuração e documentação seguem o fluxo branch → Pull Request → CI → merge.

## CloudPanel

O reverse proxy continua externo à stack e deve apontar para:

```text
http://127.0.0.1:GATEWAY_PORT
```

preservando o cabeçalho `Host`.

## Segurança operacional

Não exclua os diretórios `data-*` em atualização ou redeploy. Segredos expostos anteriormente devem ser rotacionados antes de produção.
