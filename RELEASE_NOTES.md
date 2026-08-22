# Release Notes — v1.0.0-rc.12

Esta release corrige o fluxo de provisionamento e a experiência visual da **ARGWS Financial Platform**, preservando a arquitetura image-only e os serviços existentes.

## Provisionamento operacional

- tenants só entram nas tarefas periódicas quando o domínio primário também está `ACTIVE`, eliminando erros repetitivos de `DOMAIN_NOT_ACTIVE` para ambientes ainda em reconciliação;
- o domínio provisionado passa a reconciliar o wildcard Cloudflare antes de ser marcado como ativo;
- falhas de DNS ficam registradas no job e no domínio, em vez de produzir um falso sucesso;
- o bootstrap recupera automaticamente o tenant demo existente quando ele ficou incompleto em uma execução anterior;
- ao criar ou reprocessar um tenant, o Control Plane abre diretamente o job correspondente e acompanha o progresso automaticamente;
- domínios `PROVISIONED` deixam de exibir a ação manual de verificação destinada a domínios `CUSTOM`.

## CloudPanel automático

O `financial-cloudpanel-agent` passa a criar o Reverse Proxy `finance.argws.com.br` automaticamente via `clpctl site:add:reverse-proxy` quando o VHost ainda não existe, usando o usuário e a senha configurados no `.env` e apontando por padrão para `http://127.0.0.1:18800`.

Depois da criação, o agente mantém a reconciliação do wildcard e a instalação do certificado.

## Prometheus

O hostname interno `financial-api` passa a ser aceito pelo `TrustedHostMiddleware`, permitindo que o Prometheus faça scrape de `/metrics` sem receber HTTP 400.

## Interface e responsividade

- shell administrativo mais compacto;
- sidebar reduzida e adequada a telas menores;
- header e espaçamentos reduzidos;
- botões, inputs, cards e tabelas com densidade melhor;
- tabelas agora usam rolagem horizontal no mobile, em vez de conteúdo cortado;
- criação e reprocessamento de tenant exibem progresso real;
- tela de provisionamento possui atualização automática e drawer de eventos atualizado;
- landing pública de `finance.argws.com.br` foi redesenhada com escala menor, conteúdo objetivo, CTAs para demo e Control Plane e responsividade dedicada.

## Topologia preservada

- `finance.argws.com.br` — landing pública;
- `demo.finance.argws.com.br` — demonstração;
- `control.finance.argws.com.br` — Control Plane;
- `admin.finance.argws.com.br` — alias administrativo;
- `api.finance.argws.com.br` — API;
- `*.finance.argws.com.br` — tenants;
- Prometheus e Grafana permanecem na stack;
- somente o gateway publica porta no host;
- produção continua image-only via GHCR.
