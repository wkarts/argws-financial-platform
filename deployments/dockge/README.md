# Deploy Dockge + CloudPanel

O runtime de produção da ARGWS Financeiro é **image-only**. O servidor nunca compila backend, frontend ou gateway: todos os componentes da aplicação são consumidos do GHCR com `:latest` e `pull_policy: always`.

## Contrato de exposição

A stack publica somente:

```text
127.0.0.1:${GATEWAY_PORT}:80
```

PostgreSQL, Redis, RabbitMQ, MinIO, API, workers, ACME e os demais componentes não publicam portas no host. O `financial-cloudpanel-agent` usa o namespace do host apenas para reconciliar o NGINX/CloudPanel e não abre listener próprio.

## Única ação manual no CloudPanel

Crie um único **Reverse Proxy** para o domínio principal:

```text
financeiro.seu-dominio.com.br
    ->
http://127.0.0.1:18800
```

Preserve o header `Host`. Depois dessa criação a stack assume o restante:

```text
Cloudflare API
    ↓
*.financeiro.seu-dominio.com.br  (DNS-only)
    ↓
ACME DNS-01
    ├── financeiro.seu-dominio.com.br
    └── *.financeiro.seu-dominio.com.br
    ↓
financial-cloudpanel-agent
    ├── adiciona wildcard ao server_name
    ├── valida nginx -t
    ├── instala certificado via clpctl
    ├── reconcilia o VHost novamente
    └── recarrega o NGINX
```

Assim `control.`, `api.` e os domínios provisórios das empresas passam pelo mesmo VHost e pelo mesmo gateway sem criar sites adicionais no CloudPanel.

## Pacote recomendado

Use o asset da Release:

```text
ARGWS-Financial-Platform-v<VERSAO>-Dockge.zip
```

Estrutura:

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
├── data-acme/
├── data-certs/
├── data-cloudpanel-agent/
└── secrets/
    ├── rclone.conf
    └── backup-age-identity.txt
```

Com `FINANCIAL_DATA_ROOT=.`, toda a persistência permanece visível na própria pasta da stack.

## `.env`

O exemplo foi reduzido para evitar repetição. A senha de infraestrutura é definida uma única vez:

```env
INTERNAL_SERVICES_PASSWORD=troque-por-uma-senha-url-safe-forte
```

Ela é injetada internamente em PostgreSQL, RabbitMQ, MinIO e S3. A senha inicial do administrador permanece separada:

```env
INITIAL_ADMIN_PASSWORD=troque-por-outra-senha-forte
```

Chaves criptográficas, tokens Cloudflare e secrets de webhooks continuam independentes e nunca devem reutilizar essas senhas.

## Wildcard automático

O modo padrão é:

```env
CLOUDFLARE_ENABLED=true
CLOUDFLARE_PROVISIONING_MODE=wildcard
CLOUDFLARE_PROXIED=false
CLOUDFLARE_TENANT_RECORD_TARGET=${PLATFORM_DOMAIN}
```

A aplicação garante o registro `*.TENANT_DOMAIN_ROOT` como DNS-only. Para esse modelo, o alvo precisa resolver para a mesma origem que atende o Reverse Proxy do CloudPanel; não dependa do SSL Universal da Cloudflare para um wildcard de segundo nível.

O certificado wildcard é emitido localmente por DNS-01 e instalado no CloudPanel pela própria stack.

## Primeira instalação

1. Extraia o asset `-Dockge.zip` na pasta de stacks.
2. Renomeie `.env.example` para `.env`.
3. Preencha domínio, e-mail, credenciais e Cloudflare.
4. Crie o único Reverse Proxy no CloudPanel apontando para `127.0.0.1:GATEWAY_PORT`.
5. Execute `docker compose config`.
6. Execute `docker compose pull`.
7. Execute `docker compose up -d`.

Antes das migrations, `financial-preflight` valida a configuração sem imprimir segredos. Em seguida `financial-domain-init` garante o wildcard DNS e só então a persistência e a aplicação são iniciadas.

## Verificação

```bash
docker compose ps
docker compose logs --tail=200 financial-preflight
docker compose logs --tail=200 financial-domain-init
docker compose logs --tail=200 financial-acme
docker compose logs --tail=200 financial-cloudpanel-agent
docker compose logs --tail=200 financial-rabbitmq
docker compose logs --tail=200 financial-worker-default
```

O resultado esperado de `docker compose ps` é apenas o gateway com um mapeamento de host. Os demais serviços podem mostrar suas portas internas (`5432/tcp`, `6379/tcp`, etc.), mas sem endereço/porta publicados no host.

## Build local

Nenhum deployment executa build local. O único modelo de compilação local permanece deliberadamente isolado no checkout de desenvolvimento:

```bash
docker compose -f compose.yaml -f compose.local-build.yaml up -d --build
```

Esse arquivo não faz parte do fluxo operacional do Dockge.
