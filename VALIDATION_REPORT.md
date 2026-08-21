# Relatório de Validação — ARGWS Financial Platform

A versão validada é sempre a indicada pelo arquivo [`VERSION`](VERSION). O workflow `Publish Release` regenera `VALIDATION_REPORT.json` antes de empacotar e publicar cada release.

## Contrato de validação

```text
Backend pytest:                    obrigatório
Python compileall/AST:             obrigatório
SQLAlchemy configure_mappers:      obrigatório
Validador estrutural:              obrigatório
Rotas FastAPI:                     inventariadas e sem duplicidades locais
Contrato frontend/backend:          obrigatório
Alembic heads/portabilidade:        obrigatório
TypeScript/Vue typecheck:           obrigatório
Vitest:                             obrigatório
Build Vite:                         obrigatório
Docker builds:                      api/web/gateway/acme/cloudpanel-agent
Docker smoke:                       API + Control Plane + tenant demo
Compose Docker/Dockge/CloudPanel:   obrigatório
Stack Portainer:                    obrigatória
```

## Versionamento

- `VERSION` é a única fonte de verdade;
- backend e frontend leem a versão empacotada nas imagens publicadas;
- `frontend/package.json` não duplica a versão da aplicação;
- os Dockerfiles carregam `VERSION` dentro das imagens;
- os exemplos `.env` deixam `APP_VERSION` e `VITE_APP_VERSION` vazios;
- o Compose Dockge não injeta `APP_VERSION`, evitando sobrescrever a versão da imagem;
- as imagens operacionais usam sempre `:latest`;
- o pipeline também publica alias imutável da versão e SHA para auditoria/rollback, sem tornar o runtime dependente deles.

## Publicação obrigatória

A release só é criada após:

1. CI reutilizável completa;
2. build e smoke tests;
3. publicação e verificação das cinco imagens GHCR;
4. validação estrutural final;
5. geração de ZIP, TAR.ZST e TAR.GZ;
6. geração de checksums SHA-256 e relatório do pacote;
7. upload dos artefatos do GitHub Actions;
8. criação da tag e do GitHub Release.

## Escopo verificado

São cobertos Control Plane, Tenant Plane, migrations separadas, múltiplas empresas, resolução por hostname, providers financeiros, CNAB 240/400, Pix Automático, SMTP, Evolution API, Outbox/Celery, backups, restore, Docker, Dockge, CloudPanel, Portainer, CI e publicação.

Também são verificados:

- referências de variáveis dos arquivos Compose;
- presença das filas e serviços obrigatórios;
- Compose de código-fonte separado dos Composes image-only;
- Dockge sem `build:` local e com imagens GHCR `:latest`;
- correspondência entre chamadas Axios e rotas FastAPI;
- cabeças Alembic e caminhos portáveis;
- ausência de `.env`, credenciais bootstrap e identidades reais na distribuição;
- consistência dos exemplos de ambiente;
- política de imagens `:latest` para runtime;
- empacotamento limpo com manifest e verificação de integridade.

## Homologações externas

O pipeline valida a plataforma e a distribuição, mas não substitui credenciais e homologações externas de banco/PSP, carteira, CNAB específico, NFS-e, SMTP, Evolution API, Cloudflare, Google Drive e Dropbox.
