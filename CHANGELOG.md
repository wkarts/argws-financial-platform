# Changelog

## 1.0.0-rc.2 — 2026-08-20

### Validado e corrigido

- suíte backend executada com 41 testes aprovados;
- contrato estático entre 171 chamadas HTTP do frontend e 161 rotas FastAPI validado sem divergências;
- caminhos Alembic tornados independentes do diretório atual por meio de `%(here)s`;
- empacotamento de release refeito para excluir `.git`, caches, bytecode, credenciais e dados de runtime;
- geração de `MANIFEST.sha256`, inventário do pacote e verificação automática da integridade dos arquivos;
- workflow de release preparado para usar o empacotador canônico;
- relatório de validação atualizado para a versão efetivamente entregue.

### Condição

- código-fonte e distribuição operacional completos em release candidate;
- build Docker integral e homologações bancárias/fiscais continuam dependentes do ambiente conectado e das credenciais reais.

## 1.0.0-rc.1 — 2026-08-20

### Adicionado

- Control Plane completo para tenants, planos, limites, domínios, configurações, usuários, integrações, API keys, suporte auditado, consumo, provisionamento, backup e restore;
- Tenant Plane ampliado com contatos, serviços, contratos, recebíveis, pagamentos, estornos, negociações, links públicos, importações, exportações, API keys e webhooks;
- Pix Automático com mandatos e instruções;
- CNAB 400 extensível;
- importação OFX e CSV;
- adapter Asaas;
- enforce de capacidades e limites dos planos;
- papéis e permissões padrão;
- migrations adicionais do Control Plane e Tenant Plane;
- workers especializados e migration de todos os tenants existentes;
- portal público de pagamento;
- pacotes Docker, Dockge, CloudPanel e Portainer;
- ACME DNS-01, agente CloudPanel e monitoramento opcional;
- documentação completa de deploy, produto e PR.

### Alterado

- Compose reorganizado para serviços especializados, health checks e profiles;
- contrato `.env.example` ampliado;
- frontend do Control Plane e Tenant Plane ampliado;
- Outbox e filas expandidos;
- scripts de instalação, backup, restore, atualização e rollback revisados;
- validador estrutural ampliado para código, frontend, Compose e deploys.

### Corrigido

- ausência de stack Portainer;
- pacote Dockge incompleto;
- automação CloudPanel insuficiente;
- falta de ambientes específicos;
- Control Plane demonstrativo;
- ausência de título e descrição de PR;
- nomenclatura e contratos inconsistentes da entrega Alpha.

## 0.1.0-alpha.1 — 2026-08-20

- fundação inicial da plataforma;
- fluxo financeiro Sandbox;
- primeira estrutura multitenant;
- Compose e interface parciais.
