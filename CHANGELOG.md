# Changelog

## 0.1.0-alpha.1 — 2026-08-20

### Adicionado

- Control Plane e Tenant Plane;
- banco PostgreSQL isolado por tenant;
- múltiplas empresas por tenant e RBAC por empresa;
- provisionamento de tenant, domínio e storage;
- Cloudflare provider e Domain Agent para SSL/domínios personalizados;
- clientes, serviços, contratos, recorrências e recebíveis;
- provider bancário Sandbox com boleto/PIX e PDF;
- CNAB 240 extensível, remessa e retorno;
- pagamentos, conciliação, recibos e NFS-e Sandbox;
- SMTP, Evolution API, Outbox, RabbitMQ e Celery;
- documentos imutáveis no MinIO/S3;
- backup/restore local, S3, Google Drive e Dropbox;
- importação do padrão Financeiro Vitor;
- frontend Vue 3/Tailwind PWA;
- Docker Compose, CloudPanel, Dockge, GitHub Actions e documentação completa;
- rate limiting com Redis;
- migrations Alembic explícitas para Control Plane e tenant;
- rotação automática de refresh token e logout com revogação;
- Domain Agent reconciliando domínios `WAITING_SSL` e `ACTIVE`;
- validação distinta para pacote-fonte e stack provisionada.

### Homologação pendente por terceiros

- provider bancário real;
- layout CNAB específico de banco/carteira;
- CNAB 400 específico;
- provider NFS-e real municipal/nacional;
- validação com credenciais reais SMTP/Evolution/Drive/Dropbox.
