# Deploy no Dockge

Esta pasta não é apenas documentação: contém Compose, exemplo de ambiente e scripts operacionais.

## Modo recomendado

1. Extraia o projeto inteiro no diretório de stacks do Dockge.
2. Copie `.env.example` da raiz para `.env`.
3. Execute `python3 scripts/generate_secrets.py --env .env`.
4. No Dockge, selecione o `compose.yaml` da raiz ou `deployments/dockge/compose.yaml`.
5. Execute `deployments/dockge/install.sh` na primeira instalação.

## Arquivos

- `compose.yaml`: stack completa baseada em imagens publicadas no GHCR;
- `.env.example`: variáveis mínimas para importação;
- `install.sh`: valida, constrói/sobe e espera readiness;
- `update.sh`: backup, atualização, migrations e healthcheck;
- `rollback.sh`: troca a versão das imagens;
- `healthcheck.sh`: estado dos containers e readiness.

O Dockge deve preservar o `Host` no proxy reverso do CloudPanel para que o Tenant Resolver selecione corretamente o banco isolado.
