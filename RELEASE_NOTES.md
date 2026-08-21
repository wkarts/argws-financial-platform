# Release Notes — v1.0.0-rc.2

Esta release substitui a entrega Alpha anterior e consolida a ARGWS Financial Platform como **release candidate completa no nível de código-fonte, interface, migrations, workers, segurança e distribuição operacional**.

## Correções finais de publicação

- corrigido o fluxo pós-merge para publicar a versão declarada em `VERSION` automaticamente;
- publicação automática das imagens `api`, `web`, `gateway`, `acme` e `cloudpanel-agent` no GHCR;
- criação automática da tag `v1.0.0-rc.2` e da GitHub Release após validação da CI;
- modo `images` do instalador Docker corrigido para consumir as imagens versionadas do GHCR;
- deploy Portainer alinhado ao mesmo conjunto de imagens versionadas;
- Dependabot agrupado por ecossistema, limitado e sem upgrades major automáticos;
- Tailwind CSS mantido em 3.4.x para preservar compatibilidade com a configuração PostCSS atual, evitando a migração parcial para Tailwind 4 que quebrava o build.

## Destaques

- Control Plane administrativo ampliado;
- Tenant Plane financeiro ampliado;
- banco, usuário e storage exclusivos por tenant;
- domínios provisionados e personalizados;
- planos, limites e capacidades aplicados no backend;
- usuários da plataforma, API keys e suporte temporário auditado;
- múltiplas empresas por tenant e restrição por empresa;
- pagamentos, estornos, negociações e links públicos;
- Pix Automático;
- importação OFX/CSV;
- API keys e webhooks assinados por tenant;
- CNAB 240 e CNAB 400 extensíveis;
- provider Sandbox e adapter Asaas;
- SMTP, Evolution API, Outbox e régua de cobrança;
- backup/restore e exportação de tenant;
- pacotes completos para Docker, Dockge, CloudPanel e Portainer;
- monitoramento opcional com Prometheus/Grafana;
- CI, publicação de imagens e release versionada.

## Validações específicas da rc.2

- 41 testes backend aprovados;
- frontend com typecheck, Vitest e build Vite aprovados;
- Docker smoke test completo aprovado com API, Control Plane e tenant demo saudáveis;
- builds das imagens `api`, `web`, `gateway`, `acme` e `cloudpanel-agent` aprovados;
- 161 rotas FastAPI inventariadas;
- 171 chamadas HTTP do frontend (123 contratos únicos) cruzadas com o backend, sem divergências;
- migrations Alembic validadas com heads únicos e caminhos portáveis;
- empacotador canônico com exclusão de segredos/caches, manifest interno, ZIP/TAR e checksums externos.

## Fluxo coberto

```text
Control Plane
 -> cria plano/tenant
 -> provisiona banco, usuário, storage e domínio
 -> cria empresa e administrador iniciais
 -> Tenant Plane cadastra empresas/clientes/serviços/contratos
 -> recorrência gera recebíveis
 -> cobrança registra boleto/Pix/Pix Automático
 -> SMTP/Evolution comunica o cliente
 -> pagamento, webhook, CNAB ou extrato efetua baixa/conciliação
 -> recibo/documento fiscal/documentos são gerados
 -> auditoria, exportação e backup preservam o histórico
```

## Distribuições

- Compose de build pelo fonte;
- Compose de produção por imagens versionadas no GHCR;
- Dockge com instalador, atualização, rollback e health check;
- CloudPanel com `clpctl`, vhosts, wildcard, SSL/ACME opcional, atualização e rollback;
- Portainer com stack por imagens, stack Git/source e automação pela API;
- ambientes development, staging e production.

## Condição da release candidate

A release é candidata à produção após:

1. configurar os domínios reais;
2. preencher credenciais externas;
3. homologar o banco/PSP, carteira, CNAB e NFS-e escolhidos;
4. executar teste completo de backup e restore no ambiente de destino;
5. concluir validação de segurança e operação.

Providers Sandbox continuam disponíveis para testes sem credenciais. A release não declara homologação externa que não foi efetivamente executada.
