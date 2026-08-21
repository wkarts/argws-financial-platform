# Relatório de Validação — v1.0.0-rc.2

**Data de referência:** 20 de agosto de 2026 — America/Bahia.

## Resultado local

```text
Backend pytest:                    PASS — 41 testes
Python compileall/AST:             PASS
SQLAlchemy configure_mappers:      PASS
Validador estrutural:              PASS
Rotas FastAPI estáticas:           PASS — 161 decoradores
Contrato frontend/backend:          PASS — 171 chamadas, 123 contratos, 0 divergências
Alembic heads/portabilidade:        PASS — 2 heads válidos
TypeScript/Vue sintaxe:             PASS — 66 blocos
Contrato frontend/API:              PASS — 171 chamadas / 122 contratos únicos / 0 divergências
Imports relativos frontend:        PASS
Shell scripts:                     PASS — 23 scripts
YAML/Workflows/Compose estático:    PASS — 16 arquivos YAML
Exemplos .env sem chaves duplicadas: PASS
Arquivos obrigatórios/deploys:     PASS
```

## Escopo verificado

Foram verificados: Control Plane, Tenant Plane, migrations separadas, múltiplas empresas, resolução por hostname, providers financeiros, CNAB 240/400, Pix Automático, SMTP, Evolution API, Outbox/Celery, backups, restore, Docker, Dockge, CloudPanel, Portainer, CI e release.

Também foram conferidos:

- versões canônicas entre backend, frontend, `.env.example` e `VERSION`;
- referências de variáveis dos arquivos Compose;
- presença das filas e serviços obrigatórios;
- sincronismo entre o Compose canônico e os pacotes Dockge/CloudPanel;
- correspondência entre chamadas Axios do frontend e rotas FastAPI;
- cabeças Alembic e caminhos independentes do diretório atual;
- ausência de `.env`, credenciais bootstrap e identidades reais no pacote;
- consistência dos exemplos de ambiente de desenvolvimento, staging, produção e Portainer;
- geração segura de segredos e permissões `0600` em ensaio isolado;
- empacotamento limpo com manifest e verificação de integridade.

## Limitações do ambiente de empacotamento

Não foi possível executar neste ambiente:

- `docker compose up -d --build`, porque o daemon/CLI Docker não está disponível;
- `npm install`, `vue-tsc`, Vitest e o build Vite integral, porque o ambiente não possui resolução DNS para o registro npm;
- testes reais de SMTP, Evolution API, Cloudflare, bancos, PSP, Google Drive e Dropbox, porque dependem de credenciais externas.

O repositório inclui GitHub Actions para instalar dependências, executar typecheck/test/build do frontend, validar Compose, construir todas as imagens e realizar smoke test da stack com PostgreSQL, Redis, RabbitMQ e MinIO.

## Homologações obrigatórias antes do uso financeiro real

- banco, PSP, convênio, carteira e certificado;
- layout CNAB específico da instituição;
- Pix Automático no PSP contratado;
- NFS-e municipal ou nacional;
- SMTP e Evolution API;
- Cloudflare/DNS/SSL;
- Google Drive e Dropbox;
- ensaio de backup e restore no servidor definitivo.

A classificação correta desta entrega é **release candidate completa no nível de código-fonte e distribuição operacional**, sem alegar homologações externas que não foram executadas.
