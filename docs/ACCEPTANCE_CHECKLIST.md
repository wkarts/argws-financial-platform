# Checklist de Aceite

## Plataforma

- [x] Control Plane separado por host e autenticação.
- [x] Tenant Plane resolvido por hostname.
- [x] Banco PostgreSQL por tenant.
- [x] Bucket MinIO/S3 por tenant.
- [x] Empresas múltiplas por tenant.
- [x] Usuários restritos por empresa.
- [x] Refresh token rotativo e logout com revogação.
- [x] Domínio provisionado.
- [x] Domínio personalizado e Domain Agent.
- [x] Cloudflare provider.

## Financeiro

- [x] Clientes, serviços e contratos.
- [x] Recorrência idempotente.
- [x] Contas a receber.
- [x] Cobrança Sandbox.
- [x] PIX/boleto Sandbox.
- [x] Pagamento manual e webhook.
- [x] Conciliação.
- [x] Recibo PDF.
- [x] NFS-e Sandbox XML/PDF.
- [x] Documentos imutáveis.
- [x] Auditoria.

## CNAB e bancos

- [x] Core CNAB 240 com 240 posições.
- [x] Remessa.
- [x] Parser de retorno T/U.
- [x] Idempotência de importação.
- [ ] Homologação em banco real — depende da instituição/convênio/credenciais.
- [ ] Layout CNAB 400 específico — depende do banco/carteira.

## Comunicações

- [x] SMTP.
- [x] Evolution API.
- [x] Configuração por plataforma/tenant/empresa.
- [x] Teste de integração.
- [x] Outbox/RabbitMQ/Celery.
- [x] Logs de envio/status.
- [x] Régua automática D-7/D-1/D0/D+1/D+5.
- [x] Templates editáveis e validados por canal.
- [x] Destinatários múltiplos e idempotência concorrente.

## Backup e operação

- [x] Backup do Control Plane.
- [x] Backup de todos os bancos dos tenants.
- [x] Backup de objetos.
- [x] Manifest e checksums.
- [x] S3/MinIO.
- [x] Google Drive via rclone.
- [x] Dropbox via rclone.
- [x] Restore completo.
- [x] Modo manutenção.
- [x] Retenção.

## Qualidade

- [x] Testes backend.
- [x] Testes de isolamento por empresa.
- [x] Testes de segurança e idempotência.
- [x] Testes de providers Sandbox.
- [x] Validador estrutural.
- [x] CI GitHub Actions.
- [x] Docker Compose.
- [x] CloudPanel/Dockge.
- [ ] Build Docker executado no ambiente de destino — requer daemon Docker.
- [ ] Homologação externa de SMTP/Evolution/banco/NFS-e — requer credenciais reais.
