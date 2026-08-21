# Release Notes — v1.0.0-rc.2

Esta release substitui a entrega Alpha anterior e consolida a ARGWS Financial Platform como **release candidate completa no nível de código-fonte, interface, migrations, workers, segurança e distribuição operacional**.

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
- Compose de produção por imagens;
- Dockge com instalador, atualização, rollback e health check;
- CloudPanel com `clpctl`, vhosts, wildcard, SSL/ACME opcional, atualização e rollback;
- Portainer com stack por imagens, stack Git/source e automação pela API;
- ambientes development, staging e production.

## Condição da release candidate

A release é candidata à produção após:

1. executar build e smoke tests no servidor/CI conectado;
2. configurar os domínios reais;
3. preencher credenciais externas;
4. homologar o banco/PSP, carteira, CNAB e NFS-e escolhidos;
5. executar teste completo de backup e restore no ambiente de destino;
6. concluir validação de segurança e operação.

Providers Sandbox continuam disponíveis para testes sem credenciais. A release não declara homologação externa que não foi efetivamente executada.
