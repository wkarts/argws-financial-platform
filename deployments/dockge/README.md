# Importação no Dockge

1. extraia o projeto dentro do diretório configurado como `stacksDir` do Dockge;
2. mantenha o nome `argws-financial-platform`;
3. execute `scripts/deploy_cloudpanel_dockge.sh --skip-up` para criar `.env` e segredos;
4. abra a stack no Dockge;
5. confirme o Compose;
6. faça deploy;
7. aguarde `financial-migrate` e `financial-init` terminarem com código 0;
8. confirme `/health/ready` no gateway interno.

Não edite segredos diretamente no `compose.yaml`; use `.env` com permissão restrita.
