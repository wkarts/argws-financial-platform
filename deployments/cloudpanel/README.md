# ARGWS Financeiro no CloudPanel

Este deployment foi desenhado para que a única ação manual no CloudPanel seja criar **um Reverse Proxy** para a stack Docker. Depois disso, wildcard DNS, wildcard SSL e atualização do VHost são reconciliados automaticamente pela própria stack.

## Arquitetura

```text
Cloudflare DNS
  financeiro.seu-dominio.com.br
  proxy.financeiro.seu-dominio.com.br
  *.financeiro.seu-dominio.com.br
          |
          v
CloudPanel / NGINX :443
          |
          v
http://127.0.0.1:18800
          |
          v
financial-gateway
  -> API / Web por Host header
```

A stack continua publicando somente a porta do `financial-gateway`. PostgreSQL, Redis, RabbitMQ, MinIO, API, workers e serviços auxiliares não possuem host ports.

## Única etapa manual

No CloudPanel crie um único Reverse Proxy:

```text
Domínio: financeiro.seu-dominio.com.br
Reverse Proxy URL: http://127.0.0.1:18800
```

Preserve o cabeçalho `Host`. Pode criar o Reverse Proxy antes ou depois de subir a stack; o agente aguarda o VHost existir.

Não é necessário criar site separado para `control.`, `api.` ou para cada empresa. Também não é necessário editar o VHost, instalar `acme.sh` no VPS, criar cron, importar certificado ou criar TXT ACME manualmente.

## Cloudflare e wildcard DNS

No `.env`, informe apenas as credenciais da zone e mantenha:

```env
CLOUDFLARE_ENABLED=true
CLOUDFLARE_PROVISIONING_MODE=wildcard
CLOUDFLARE_PROXIED=false
CLOUDFLARE_TENANT_RECORD_TARGET=proxy.${PLATFORM_DOMAIN}
```

O `financial-domain-init` consulta pela API Cloudflare o registro atual de `PLATFORM_DOMAIN`, obtém a origem configurada e converge automaticamente para:

```text
proxy.financeiro.seu-dominio.com.br   A/AAAA/CNAME  <mesma origem do domínio principal>   DNS-only
*.financeiro.seu-dominio.com.br       CNAME         proxy.financeiro.seu-dominio.com.br   DNS-only
```

Se o domínio principal estiver com proxy da Cloudflare, o IP/origem real ainda é lido pelo registro da zone via API. Assim não é preciso duplicar o IP público no `.env`, e os subdomínios wildcard chegam ao CloudPanel para usar o certificado local.

## ACME DNS-01 automático

`financial-acme` solicita um certificado contendo:

```text
financeiro.seu-dominio.com.br
*.financeiro.seu-dominio.com.br
```

A validação usa DNS-01 pela API Cloudflare. Os TXT `_acme-challenge` são temporários, criados e removidos automaticamente pelo ACME.

O certificado e a chave ficam em `./data-certs`, enquanto o estado do ACME fica em `./data-acme`.

## Automação do VHost CloudPanel

`financial-cloudpanel-agent` é o único helper root-equivalent ao VPS. Ele não possui endpoint e não publica portas. O serviço:

1. aguarda o VHost do domínio principal existir;
2. localiza o arquivo real em `/etc/nginx/sites-enabled`;
3. garante `server_name <domínio> *.<domínio>;`;
4. faz backup antes da alteração;
5. executa `nginx -t` e reverte automaticamente se a validação falhar;
6. aguarda o certificado wildcard do ACME;
7. instala/renova o certificado com `clpctl site:install:certificate`;
8. reconcilia novamente o `server_name` caso o CloudPanel regenere o VHost;
9. valida e recarrega o NGINX.

O agente usa `privileged: true`, `pid: host`, `network_mode: host` e `/:/host:rw` exclusivamente para operar o CloudPanel/NGINX do VPS. Esse serviço deve ser tratado como acesso root ao host; nenhum serviço de aplicação recebe esse privilégio.

## Resultado

Depois da criação do único Reverse Proxy e do primeiro `docker compose up -d`:

```text
control.financeiro.seu-dominio.com.br
api.financeiro.seu-dominio.com.br
empresa-a.financeiro.seu-dominio.com.br
empresa-b.financeiro.seu-dominio.com.br
```

já são resolvidos pelo mesmo wildcard DNS, cobertos pelo mesmo wildcard SSL e aceitos pelo mesmo VHost CloudPanel. O roteamento final continua sendo feito pelo gateway conforme o `Host` recebido.

## Diagnóstico

```bash
docker compose logs --tail=200 financial-domain-init
docker compose logs --tail=200 financial-acme
docker compose logs --tail=200 financial-cloudpanel-agent
docker compose ps
```

No `docker compose ps`, somente `financial-gateway` deve apresentar um mapeamento como `127.0.0.1:18800->80/tcp`.
