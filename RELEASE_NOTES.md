# Release Notes — v1.0.0-rc.16

Esta release corrige o travamento do **Tenant Plane** imediatamente após autenticação bem-sucedida.

## Causa raiz

O router possuía duas rotas-filhas diferentes usando o mesmo caminho vazio (`path: ''`) sob `/`: uma para o dashboard do Control Plane e outra para o dashboard do Tenant Plane. Como a rota do Control Plane era registrada primeiro, um acesso tenant a `/` podia resolver inicialmente para o dashboard administrativo. O guard identificava o plano incorreto e redirecionava novamente para `/`, criando um ciclo de navegação sem chegar ao dashboard tenant.

O sintoma em produção era consistente: o login do tenant retornava `200`, porém nenhuma chamada funcional como `/api/v1/context` ou `/api/v1/dashboard` era disparada em seguida.

## Correção

- remove os dois dashboards concorrentes com `path: ''`;
- cria uma única rota raiz neutra chamada `home`;
- adiciona `PlaneDashboardPage.vue`, que escolhe `ControlDashboardPage` ou `TenantDashboardPage` de acordo com o hostname/plano já identificado pelo auth store;
- redirects de plano incorreto passam a apontar para a rota nomeada `home`, evitando loop para o mesmo path;
- mantém `/` como URL inicial tanto do Control Plane quanto do Tenant Plane;
- mantém autenticação e sessão isoladas por hostname;
- adiciona testes para garantir que `/` resolva em uma única rota e que o dashboard correto seja renderizado para cada plano.

## Resultado esperado

Após login em `demo.finance.argws.com.br` ou outro hostname tenant:

1. autenticação retorna sucesso;
2. frontend navega para `/` sem loop;
3. `AppLayout` carrega `/api/v1/context`;
4. `TenantDashboardPage` carrega `/api/v1/dashboard`;
5. menu e conteúdo do Tenant Plane ficam disponíveis normalmente.

No `control.finance.argws.com.br`, `/` continua renderizando o dashboard do Control Plane.

## Topologia preservada

- `finance.argws.com.br` — landing pública;
- `demo.finance.argws.com.br` — demonstração;
- `control.finance.argws.com.br` — Control Plane;
- `admin.finance.argws.com.br` — alias administrativo;
- `api.finance.argws.com.br` — API;
- `*.finance.argws.com.br` — tenants;
- produção continua image-only via GHCR `:latest`.
