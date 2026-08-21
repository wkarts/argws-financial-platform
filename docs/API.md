# API

## Política de hostname

A API financeira do Tenant Plane deve ser chamada pelo domínio provisionado ou personalizado do próprio tenant:

```text
https://<slug>.financeiro.exemplo.com.br/api/v1/...
https://financeiro.cliente.com.br/api/v1/...
```

O hostname é parte do isolamento: ele resolve o tenant e seleciona o banco PostgreSQL exclusivo correspondente. O host central `api.financeiro.exemplo.com.br` é reservado para saúde, documentação OpenAPI e informações públicas da API. As APIs administrativas do Control Plane exigem `control.financeiro.exemplo.com.br`; o host central não substitui o hostname do tenant em operações financeiras.

Webhooks bancários, fiscais e da Evolution API também usam o hostname do tenant. Não existe fallback entre tenants.

# API REST

Documentação OpenAPI em execução:

```text
/api/docs
/api/redoc
/api/openapi.json
```

## Control Plane

Host: `control.<dominio-base>`

```text
POST   /api/control/v1/auth/login
POST   /api/control/v1/auth/refresh
POST   /api/control/v1/auth/logout
GET    /api/control/v1/auth/me
GET    /api/control/v1/dashboard
GET    /api/control/v1/tenants
POST   /api/control/v1/tenants
GET    /api/control/v1/tenants/{id}
PATCH  /api/control/v1/tenants/{id}
POST   /api/control/v1/tenants/{id}/provision
POST   /api/control/v1/tenants/{id}/domains
POST   /api/control/v1/domains/{id}/verify
GET    /api/control/v1/backups
POST   /api/control/v1/backups
```

## Tenant Plane

Host: `<tenant>.<dominio-base>` ou domínio personalizado ativo.

```text
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
GET    /api/v1/auth/me
GET    /api/v1/context
GET    /api/v1/dashboard
GET    /api/v1/companies
POST   /api/v1/companies
GET    /api/v1/customers
POST   /api/v1/customers
GET    /api/v1/services
POST   /api/v1/services
GET    /api/v1/contracts
POST   /api/v1/contracts
GET    /api/v1/receivables
POST   /api/v1/receivables
POST   /api/v1/recurrences/generate
GET    /api/v1/charges
POST   /api/v1/charges
GET    /api/v1/payments
POST   /api/v1/payments
POST   /api/v1/cnab/remittances
POST   /api/v1/cnab/returns
GET    /api/v1/reconciliations
POST   /api/v1/reconciliations
POST   /api/v1/reconciliations/auto-match
GET    /api/v1/integrations
PUT    /api/v1/integrations/{provider}
GET    /api/v1/notification-rules
POST   /api/v1/notification-rules
POST   /api/v1/notification-rules/run
PUT    /api/v1/notification-rules/{id}
DELETE /api/v1/notification-rules/{id}
GET    /api/v1/notification-templates
POST   /api/v1/notification-templates
PUT    /api/v1/notification-templates/{id}
DELETE /api/v1/notification-templates/{id}
POST   /api/v1/notifications/test
GET    /api/v1/notifications
GET    /api/v1/audit
POST   /api/v1/receipts
POST   /api/v1/fiscal-documents
GET    /api/v1/documents
POST   /api/v1/imports/financial-vitor/preview
POST   /api/v1/imports/financial-vitor
```

## Envelope

Sucesso:

```json
{
  "data": {},
  "meta": {}
}
```

Erro:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Mensagem legível",
    "details": {}
  }
}
```

## Correlação

Envie opcionalmente:

```text
X-Request-ID: uuid-ou-identificador
```

A resposta devolve o mesmo cabeçalho, e eventos/erros o utilizam na auditoria.
