# Relatório de Validação — v0.1.0-alpha.1

## Resultado

```text
Backend pytest:               PASS — 38 testes
Python compileall:            PASS
SQLAlchemy configure_mappers: PASS
Validador estrutural:         PASS
Rotas FastAPI estáticas:      PASS — 85 rotas, sem duplicidades
TypeScript/Vue sintaxe:       PASS — 35 blocos
Imports relativos frontend:  PASS
Shell/Python scripts:         PASS
YAML/Workflows:               PASS
Deploy --skip-up:             PASS
```

## Ensaio CloudPanel/Dockge

O instalador foi executado sobre uma cópia temporária com:

```text
PLATFORM_DOMAIN=financeiro.exemplo.com.br
CONTROL_PLANE_HOST=control.financeiro.exemplo.com.br
API_HOST=api.financeiro.exemplo.com.br
TENANT_DOMAIN_ROOT=financeiro.exemplo.com.br
```

Foram verificados:

- geração de segredos fortes;
- igualdade entre credenciais administrativas PostgreSQL esperadas;
- igualdade entre credenciais internas MinIO/S3;
- `.env` com modo `0600`;
- `.bootstrap-credentials.txt` com modo `0600`;
- ausência de contaminação do pacote-fonte por arquivos de runtime.

## Arquivo legado de referência

Validação somente leitura do `FINANCEIRO Vitor.zip`:

```text
Competência:             2026-07
Registros consolidados:  319
Honorários:               317
Boletos lidos:            188
Recibos lidos:            145
Notas associadas:          37
Contatos associados:       43
Valor consolidado: R$ 523.671,37
```

A prévia sinalizou cadastros sem CPF/CNPJ ou contato suficiente para revisão humana antes da importação definitiva. Os dados originais não integram o pacote distribuído.

## Limites da validação local

Não foi possível executar neste ambiente:

- `docker compose up -d --build`, por ausência do daemon Docker;
- `npm install`, `vue-tsc`, Vitest e build Vite completos, por indisponibilidade do registro npm.

Essas validações estão configuradas no GitHub Actions e nos profiles Docker `financial-api-test` e `financial-web-test`.

## Homologações externas

Permanecem obrigatórias antes do uso financeiro real:

- banco, convênio e carteira;
- layout CNAB específico do banco;
- NFS-e municipal ou nacional;
- credenciais SMTP/Evolution API;
- Google Drive/Dropbox;
- DNS, Cloudflare e certificados do domínio definitivo.
