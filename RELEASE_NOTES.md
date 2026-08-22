# Release Notes — v1.0.0-rc.15

Esta release corrige o estado residual `FAILED / DNS ERROR / SSL PENDING` observado no provisionamento de tenants da **ARGWS Financial Platform** quando o wildcard da plataforma já existe, mas o token usado pelo backend recebe `401/403` ao consultar a API REST da Cloudflare.

## Wildcard compartilhado da plataforma

Em `CLOUDFLARE_PROVISIONING_MODE=wildcard`, o wildcard `*.finance.argws.com.br` é infraestrutura compartilhada da plataforma. O ambiente real já possui o registro wildcard apontando para o servidor e o certificado wildcard é emitido pelo ACME e instalado automaticamente pelo CloudPanel Agent.

A rc.15 ajusta o provider para que:

- `401/403` da API REST da Cloudflare durante `ensure_managed_wildcard()` não marque o tenant como falho quando o modo ativo é `wildcard`;
- o provider retorna o wildcard compartilhado como infraestrutura externa da plataforma e permite que o retry conclua o restante do provisionamento;
- o modo `records` continua estrito: erros HTTP permanecem fatais e não são mascarados;
- erros diferentes de `401/403` continuam sendo propagados normalmente;
- foram adicionados testes específicos cobrindo o fallback de wildcard compartilhado e garantindo que o modo `records` não seja relaxado.

## Resultado esperado após retry

Ao reprocessar um tenant provisório já coberto por `*.finance.argws.com.br`, o job deve avançar de `DOMAIN 70%` para `BOOTSTRAP`, `VALIDATION` e `COMPLETED`, limpando `last_error` e atualizando o domínio para `ACTIVE` com SSL `ACTIVE` quando `PUBLIC_SCHEME=https`.

## Topologia preservada

- `finance.argws.com.br` — landing pública;
- `demo.finance.argws.com.br` — demonstração;
- `control.finance.argws.com.br` — Control Plane;
- `admin.finance.argws.com.br` — alias administrativo;
- `api.finance.argws.com.br` — API;
- `*.finance.argws.com.br` — tenants;
- somente `financial-gateway` publica porta no host;
- PostgreSQL, Redis, RabbitMQ, MinIO, Prometheus e Grafana continuam internos;
- produção continua image-only via GHCR `:latest`.
