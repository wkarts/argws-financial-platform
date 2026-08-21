# Checklist de Aceite — v1.0.0-rc.2

## Control Plane e multitenancy

- [x] Control Plane separado por host, autenticação e autorização.
- [x] Tenant Plane resolvido por hostname sem fallback.
- [x] Banco PostgreSQL e usuário exclusivos por tenant.
- [x] Storage segregado por tenant.
- [x] Empresas múltiplas por tenant.
- [x] Usuários e permissões por empresa.
- [x] Domínio provisionado e domínios personalizados.
- [x] Cloudflare Provider e estados DNS/SSL.
- [x] Planos, feature flags, limites e enforcement no backend.
- [x] Usuários e papéis da plataforma.
- [x] API keys da plataforma.
- [x] Suporte temporário auditado.
- [x] Auditoria e consumo global.
- [x] Provisionamento, suspensão, reativação, cancelamento e arquivamento.

## Financeiro do tenant

- [x] Clientes e múltiplos contatos.
- [x] Serviços.
- [x] Contratos.
- [x] Recorrência idempotente.
- [x] Contas a receber.
- [x] Cobranças.
- [x] Pagamentos total/parcial.
- [x] Estorno.
- [x] Conciliação.
- [x] Importação OFX/CSV.
- [x] Negociações/acordos.
- [x] Links públicos de pagamento.
- [x] Recibos PDF.
- [x] Documentos imutáveis.
- [x] Importações e exportações.
- [x] Relatórios e dashboards.

## Bancos, Pix e CNAB

- [x] Provider bancário Sandbox.
- [x] Adapter Asaas configurável.
- [x] Boleto/Pix/boleto híbrido em Sandbox.
- [x] Pix Automático com mandato e instrução.
- [x] CNAB 240 extensível.
- [x] CNAB 400 extensível.
- [x] Remessas, retornos e eventos.
- [x] Idempotência.
- [ ] Homologação de uma carteira/convênio real — depende da instituição e credenciais.
- [ ] Homologação Pix Automático real — depende do PSP e contrato.

## Fiscal e comunicação

- [x] NFS-e Sandbox XML/PDF.
- [x] SMTP por plataforma/tenant/empresa.
- [x] Evolution API por plataforma/tenant/empresa.
- [x] Webhook Evolution idempotente.
- [x] Régua de cobrança.
- [x] Templates.
- [x] Outbox/RabbitMQ/Celery.
- [x] API keys do tenant.
- [x] Webhooks de saída assinados e com retry.
- [ ] NFS-e real — depende do provedor, certificado e credenciais.
- [ ] Teste real SMTP/Evolution — depende das credenciais do ambiente.

## Deploy e infraestrutura

- [x] Compose de build pelo fonte.
- [x] Compose de produção por imagens.
- [x] Docker genérico.
- [x] Dockge com ambiente, compose, install, update, rollback e health check.
- [x] CloudPanel com ambiente, compose, install, update, rollback, health check e vhosts.
- [x] Portainer com stack por imagens, stack Git/source, deploy API e webhook.
- [x] Migrations do Control Plane.
- [x] Migrations de todos os tenants existentes.
- [x] Bootstrap idempotente.
- [x] Health, live, ready e metrics.
- [x] Prometheus/Grafana opcionais.
- [x] `.env.example` completo e exemplos por ambiente.
- [x] GitHub Actions para CI, imagens e release.
- [x] Contrato frontend/backend sem chamadas órfãs.
- [x] Alembic com heads únicos e caminhos portáveis.
- [x] Empacotamento limpo com manifest e checksums.
- [ ] Smoke test Docker neste ambiente de empacotamento — requer daemon Docker.
- [ ] Build npm integral neste ambiente de empacotamento — requer acesso ao registry npm.

## Backup e segurança

- [x] Backup Control Plane.
- [x] Backup dos bancos dos tenants.
- [x] Backup MinIO/S3.
- [x] Google Drive via rclone.
- [x] Dropbox via rclone.
- [x] Manifest, checksums e criptografia opcional.
- [x] Restore completo.
- [x] Exportação/restore de tenant no Control Plane.
- [x] Segredos fora do código.
- [x] Auditoria append-only.
- [x] API keys por hash.
- [x] Webhooks assinados.
- [x] Rate limit e locks distribuídos.
- [ ] Restore real em produção — deve ser validado no ambiente de destino antes do go-live.
