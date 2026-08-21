# Deploy no Dockge

## Objetivo

Executar a ARGWS Financial Platform em uma stack gerenciada pelo Dockge, mantendo o código-fonte, o Compose, os segredos e os volumes persistentes no diretório configurado para stacks.

## Arquivos entregues

```text
deployments/dockge/
├── .env.example
├── compose.yaml
├── install.sh
├── update.sh
├── rollback.sh
├── healthcheck.sh
└── README.md
```

O `compose.yaml` desta pasta é sincronizado com o Compose principal de build a partir do código-fonte.

## Pré-requisitos

- Linux 64-bit;
- Docker Engine;
- Docker Compose v2;
- Dockge instalado;
- Python 3 para geração inicial dos segredos;
- acesso ao diretório de stacks do Dockge;
- proxy reverso externo para a porta do gateway, normalmente `127.0.0.1:8800`.

## Instalação automatizada

A partir da raiz do pacote:

```bash
sudo ./deployments/dockge/install.sh \
  --domain financeiro.exemplo.com.br \
  --admin-email admin@exemplo.com.br \
  --stacks-dir /opt/stacks \
  --stack-name argws-financial-platform
```

Para somente preparar os arquivos, sem subir containers:

```bash
sudo ./deployments/dockge/install.sh \
  --domain financeiro.exemplo.com.br \
  --admin-email admin@exemplo.com.br \
  --stacks-dir /opt/stacks \
  --stack-name argws-financial-platform \
  --skip-up
```

O instalador:

1. copia a aplicação para o diretório da stack;
2. cria `.env` a partir do contrato completo;
3. gera chaves e senhas fortes;
4. cria diretórios persistentes e arquivos de runtime;
5. valida o projeto e o Compose;
6. executa build e sobe a stack, quando `--skip-up` não for informado;
7. aguarda o endpoint `/health/ready`;
8. mantém as credenciais iniciais em `.bootstrap-credentials.txt`, com permissão restrita.

## Importação no Dockge

Após `--skip-up`:

1. abra o Dockge;
2. use **Scan Stacks Folder**;
3. selecione `argws-financial-platform`;
4. revise `compose.yaml` e `.env`;
5. execute o deploy;
6. confirme que `financial-migrate`, `financial-migrate-tenants` e `financial-bootstrap` finalizam com código zero;
7. confirme API, workers, beat, web e gateway em execução.

## Atualização

```bash
cd /opt/stacks/argws-financial-platform
./deployments/dockge/update.sh
```

A atualização executa backup prévio, validação, rebuild com `--pull`, migrations do Control Plane, migrations dos tenants existentes, bootstrap e readiness.

## Rollback

```bash
cd /opt/stacks/argws-financial-platform
./deployments/dockge/rollback.sh /caminho/do/backup.tar.zst
```

O rollback restaura o backup informado e volta a subir a stack. Para rollback apenas de imagem/código sem restauração, preserve uma cópia/tag anterior do repositório e execute o Compose correspondente.

## Health check

```bash
./deployments/dockge/healthcheck.sh
```

Também é possível verificar diretamente:

```bash
docker compose --env-file .env -f compose.yaml ps
curl -fsS http://127.0.0.1:8800/health/live
curl -fsS http://127.0.0.1:8800/health/ready
```

## Volumes e backups

Os caminhos persistentes são definidos no `.env`. Não remova volumes, diretórios de dados ou o arquivo de identidade `age` sem um backup validado. Consulte `BACKUP_RESTORE.md`.
