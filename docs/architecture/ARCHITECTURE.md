# Arquitetura da ARGWS Financial Platform

## 1. Princípios

A plataforma segue os princípios abaixo:

1. isolamento de tenant por banco de dados;
2. isolamento de empresa dentro do tenant;
3. Control Plane independente do Tenant Plane;
4. tenant resolvido por hostname;
5. transações financeiras idempotentes;
6. integrações externas atrás de providers;
7. eventos financeiros publicados por Transactional Outbox;
8. documentos financeiros imutáveis e auditáveis;
9. processamento assíncrono com retry e filas duráveis;
10. backup verificável e restore executável.

## 2. Topologia lógica

```text
Internet
   |
Cloudflare / DNS / SSL
   |
CloudPanel / Nginx
   |
financial-gateway :8800
   |-------------------------------|
   |                               |
financial-web                  financial-api
                                   |
                 |-----------------|-------------------|
                 |                 |                   |
             PostgreSQL          Redis              RabbitMQ
                 |                                     |
          Control database                       Celery Workers
          Tenant databases                              |
                                                     MinIO/S3
```

## 3. Control Plane

O Control Plane usa o banco central `financial_platform` e contém somente metadados da plataforma:

- tenants;
- domínios;
- bancos de dados de tenant;
- storage de tenant;
- jobs de provisionamento;
- usuários da plataforma;
- auditoria global;
- estado de backups.

Rotas:

```text
/api/control/v1/*
```

Host obrigatório em produção:

```text
control.<dominio-base>
```

Usuários do tenant não autenticam no Control Plane.

## 4. Tenant Plane

Cada tenant possui:

- banco PostgreSQL exclusivo;
- papel PostgreSQL exclusivo e sem privilégios administrativos;
- bucket MinIO/S3 exclusivo;
- domínio provisionado;
- zero ou vários domínios personalizados;
- empresa inicial;
- administrador inicial;
- templates e régua de cobrança iniciais.

Rotas:

```text
/api/v1/*
```

A API resolve o tenant antes de abrir a sessão do banco.

## 5. Resolução por hostname

```text
Host HTTP
   |
TenantResolver.normalize_hostname
   |
Redis domain:<hostname>
   |
Control database / tenant_domains
   |
TenantContext
   |
TenantEngineRegistry
   |
Banco exclusivo do tenant
```

Condições obrigatórias:

- hostname cadastrado;
- domínio `ACTIVE`;
- tenant `ACTIVE`;
- token JWT com o mesmo `tenant_id` do hostname.

Não existe fallback para um tenant padrão em produção.

## 6. Isolamento por empresa

Dentro do banco do tenant, entidades financeiras possuem `company_id`.

`UserCompany` determina os CNPJs que o usuário pode operar. As consultas financeiras aplicam o filtro de empresas acessíveis, e endpoints de gravação usam `ensure_company_access`.

`TENANT_ADMIN` pode operar todas as empresas do tenant. Usuários restritos acessam somente empresas explicitamente vinculadas.

## 7. Providers

### BankingProvider

```python
create_charge(request)
cancel_charge(external_id)
get_charge(external_id)
```

O registro inicial contém `SANDBOX`. Providers reais são registrados sem alterar contratos, recebíveis ou pagamentos.

### InvoiceProvider

Produz documento fiscal e mantém a implementação municipal/nacional isolada.

### NotificationProvider

SMTP e Evolution API usam configuração com precedência:

```text
Empresa > Tenant > Plataforma
```

### BackupProvider

Destinos suportados:

```text
Local
S3/MinIO
Google Drive via rclone
Dropbox via rclone
```

## 8. Outbox transacional

Fluxo:

```text
BEGIN
  altera recebível
  registra pagamento
  cria outbox_event
COMMIT
   |
Outbox Worker
   |
RabbitMQ
   |
Workers especializados
```

Isso impede que um pagamento seja confirmado no banco e sua notificação seja perdida por falha entre sistemas.

## 9. Idempotência

Chaves idempotentes são aplicadas em:

- recorrência;
- criação de cobrança;
- webhook bancário;
- webhook Evolution;
- pagamento externo;
- importação CNAB;
- conciliação;
- importação legada.

Constraints únicas no PostgreSQL são a última barreira contra duplicação concorrente.

## 10. Documentos

Os objetos financeiros são armazenados com:

- bucket/prefixo do tenant;
- prefixo da empresa;
- UUID de documento;
- SHA-256;
- MIME type;
- tamanho;
- origem;
- entidade relacionada;
- data e usuário.

Arquivos críticos não são sobrescritos. Uma correção gera novo objeto e nova versão lógica.

## 11. Segurança

- Argon2id para senhas;
- JWT de acesso e refresh separados por plano;
- rotação/revogação de sessão;
- criptografia Fernet de credenciais externas;
- Trusted Hosts;
- validação de host;
- CORS explícito;
- segredos fora do repositório;
- auditoria append-only;
- cabeçalhos de segurança;
- limite de tamanho de upload;
- validação de ZIP contra traversal e expansão excessiva.

## 12. Escalabilidade

A API e os workers são stateless. É possível aumentar:

```bash
docker compose up -d --scale financial-api=3 --scale financial-worker=4
```

Para múltiplas réplicas da API, o gateway deve balancear os containers ou a implantação deve migrar para um orquestrador. O banco do Control Plane permanece compartilhado, enquanto cada tenant continua fisicamente isolado.
