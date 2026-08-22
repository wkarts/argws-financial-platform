# Release Notes — v1.0.0-rc.8

Esta release corrige a operação real observada no primeiro deploy público da ARGWS Financeiro e consolida três pontos: **login profissional sem exposição da implementação**, **compatibilidade Celery/RabbitMQ 4** e **wildcard DNS/SSL automático no CloudPanel**.

## Login voltado ao negócio

A tela de acesso foi redesenhada mantendo a identidade financeira em azul-marinho/verde, com melhor hierarquia visual, responsividade e acessibilidade.

Foram removidas da interface pública referências como Python, FastAPI, PostgreSQL, Vue, SaaS, multitenancy e detalhes de arquitetura. O usuário passa a encontrar apenas linguagem relacionada à operação financeira, segurança, cobranças, recebimentos e conciliação.

A mesma tela diferencia de forma discreta a área financeira e a área administrativa sem expor a implementação da plataforma.

## RabbitMQ 4 / Celery

Os logs de produção mostraram que autenticação e acesso ao vhost estavam corretos, mas o `pidbox` do Celery tentava declarar `transient_nonexcl_queues`, recurso bloqueado por padrão no RabbitMQ 4.

A configuração do Celery agora mantém `worker_enable_remote_control=False`, eliminando a fila transitória de controle remoto que causava reconexões contínuas e `RestartFreqExceeded`.

Também foi ativado `worker_cancel_long_running_tasks_on_connection_loss=True`, coerente com tarefas de ACK tardio.

A CI passa a manter os workers ativos durante o smoke test e falha se voltar a aparecer `transient_nonexcl_queues` nos logs.

## CloudPanel: um Reverse Proxy, wildcard automático

No host CloudPanel, a única etapa manual esperada passa a ser criar o Reverse Proxy do domínio principal para:

```text
http://127.0.0.1:${GATEWAY_PORT}
```

O runtime Dockge/CloudPanel adiciona três componentes sem publicar portas adicionais:

- `financial-domain-init`: garante `*.TENANT_DOMAIN_ROOT` no Cloudflare em modo DNS-only;
- `financial-acme`: emite/renova certificado para o domínio base + wildcard via DNS-01;
- `financial-cloudpanel-agent`: localiza o VHost criado pelo CloudPanel, adiciona o wildcard ao `server_name`, valida `nginx -t` e instala/renova o certificado via `clpctl`.

O agente mantém backup do VHost, revalida o wildcard depois de alterações do CloudPanel e não expõe interface HTTP própria.

Esse modelo cobre `control.`, `api.` e os domínios provisórios das empresas com um único VHost e um único certificado wildcard.

## `.env.example` simplificado

Os exemplos de Dockge e CloudPanel foram reorganizados para que a primeira instalação exija poucas alterações.

A repetição de credenciais internas foi reduzida para:

```env
INTERNAL_SERVICES_PASSWORD=...
INITIAL_ADMIN_PASSWORD=...
```

A senha interna é injetada pelo Compose em PostgreSQL, RabbitMQ, MinIO e S3. Chaves criptográficas, tokens Cloudflare e secrets de webhook permanecem independentes.

Variáveis de portas administrativas de RabbitMQ, MinIO, Prometheus e Grafana foram removidas do exemplo CloudPanel/Dockge porque esses serviços não publicam host ports.

## Segurança de rede preservada

A regra continua absoluta: somente `financial-gateway` possui `ports:`. PostgreSQL, Redis, RabbitMQ, MinIO, API, workers e componentes de automação permanecem sem publicação direta no host.

Todos os deployments de produção continuam image-only e consomem as imagens GHCR `:latest`. Build local permanece exclusivamente em `compose.local-build.yaml`, para desenvolvimento/CI.
