# Deploy no Dockge

A stack Dockge é **image-only**: consome exclusivamente imagens publicadas no GHCR e nunca compila backend/frontend no servidor.

## Pacote recomendado

Nas Releases, use:

```text
ARGWS-Financial-Platform-v<VERSAO>-Dockge.zip
```

O bundle traz `compose.yaml`, `.env.example`, README, manifesto, `data-*` e `secrets/` prontos para a pasta da stack. O `compose.yaml` do bundle é o mesmo contrato de runtime canônico do projeto.

## Estrutura operacional

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
├── data-celery/
└── secrets/
    ├── rclone.conf
    └── backup-age-identity.txt
```

Com `FINANCIAL_DATA_ROOT=.`, todos os dados ficam visíveis nessa pasta.

## Imagens

```text
ghcr.io/wkarts/argws-financial-api:latest
ghcr.io/wkarts/argws-financial-web:latest
ghcr.io/wkarts/argws-financial-gateway:latest
```

O runtime usa `pull_policy: always` fixo. As tags versionadas existem somente para auditoria e rollback explícito.

## Rede: somente uma porta no host

A única publicação de porta é:

```text
127.0.0.1:${GATEWAY_PORT}:80
```

PostgreSQL, Redis, RabbitMQ e MinIO não possuem `ports:` no runtime. As portas internas continuam disponíveis entre containers pela rede `financial-internal`, mas não ficam acessíveis diretamente no host ou na Internet.

O CloudPanel deve apontar o reverse proxy somente para:

```text
http://127.0.0.1:${GATEWAY_PORT}
```

## Preflight obrigatório

Antes de iniciar storage/migrations, `financial-preflight` valida a configuração sem rede e sem imprimir segredos. Erros de senha divergente, placeholders, SMTP inválido ou credenciais MinIO/S3 inconsistentes aparecem antes de migrations.

Para executar manualmente:

```bash
docker compose run --rm financial-preflight
```

Para reparar placeholders e relações derivadas sem regenerar os segredos reais já válidos:

```bash
python3 scripts/generate_secrets.py --env .env
```

Não use `--force` em uma stack com dados sem planejar a rotação das credenciais primárias.

## Primeira instalação

1. Extraia o bundle `-Dockge.zip` no diretório de stacks.
2. Renomeie `.env.example` para `.env`.
3. Ajuste domínio, e-mail e segredos.
4. Mantenha `FINANCIAL_DATA_ROOT=.`.
5. Execute `python3 scripts/generate_secrets.py --env .env` quando os scripts estiverem disponíveis; no bundle mínimo, preencha os placeholders manualmente.
6. Valide: `docker compose config`.
7. Baixe: `docker compose pull`.
8. Suba: `docker compose up -d`.

Se aparecer `[+] Building`, algum arquivo diferente do runtime canônico está sendo usado. Nenhum arquivo em `deployments/` contém build local.

## Build local

Build local é deliberadamente separado de deploy. No checkout completo do repositório:

```bash
docker compose -f compose.yaml -f compose.local-build.yaml up -d --build
```

`compose.local-build.yaml` não é usado pelo Dockge.

## Atualização

```bash
./deployments/dockge/update.sh
```

O script preserva `data-*`, remove override de rollback, executa backup, volta ao canal `:latest`, faz `pull` e valida readiness.

## Rollback

```bash
./deployments/dockge/rollback.sh 1.0.0-rc.7
```

O rollback cria um override temporário com aliases imutáveis. `financial-preflight` permanece em `latest`. Execute `update.sh` para voltar integralmente ao runtime `:latest`.

## Logs

Os containers usam logging Docker com rotação. Para inspeção operacional local:

```bash
docker compose logs --tail=200 financial-preflight
docker compose logs --tail=200 financial-migrate
docker compose logs --tail=200 financial-api
```

A arquitetura de auditoria centralizada pelo Control Plane está documentada em `docs/architecture/RUNTIME_EXPOSURE_AND_OPERATIONS.md` e não exige publicação permanente de portas internas.
