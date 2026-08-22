const roleLabels: Record<string, string> = {
  TENANT_ADMIN: 'Administrador',
  FINANCE_MANAGER: 'Gestor financeiro',
  FINANCE_OPERATOR: 'Operador financeiro',
  COLLECTION_OPERATOR: 'Operador de cobrança',
  TREASURY: 'Tesouraria',
  FISCAL: 'Fiscal',
  AUDITOR: 'Auditoria',
  VIEWER: 'Consulta',
  PLATFORM_ADMIN: 'Administrador da plataforma',
  PLATFORM_SUPERADMIN: 'Administrador da plataforma',
  PLATFORM_SUPPORT: 'Suporte da plataforma',
  PLATFORM_AUDITOR: 'Auditoria da plataforma',
}

const permissionLabels: Record<string, string> = {
  'dashboard.read': 'Visualizar painel financeiro',
  'companies.read': 'Visualizar empresas',
  'companies.create': 'Cadastrar empresas',
  'companies.update': 'Editar empresas',
  'customers.read': 'Visualizar clientes',
  'customers.create': 'Cadastrar clientes',
  'customers.update': 'Editar clientes',
  'services.read': 'Visualizar serviços',
  'services.create': 'Cadastrar serviços',
  'services.update': 'Editar serviços',
  'contracts.read': 'Visualizar contratos',
  'contracts.create': 'Cadastrar contratos',
  'contracts.update': 'Editar contratos',
  'receivables.read': 'Visualizar contas a receber',
  'receivables.create': 'Cadastrar contas a receber',
  'receivables.update': 'Editar contas a receber',
  'charges.read': 'Visualizar cobranças',
  'charges.create': 'Gerar cobranças',
  'payments.read': 'Visualizar pagamentos',
  'payments.create': 'Registrar pagamentos',
  'banking.read': 'Visualizar bancos e convênios',
  'banking.manage': 'Administrar bancos e convênios',
  'cnab.read': 'Visualizar arquivos CNAB',
  'cnab.generate': 'Gerar remessas CNAB',
  'cnab.import': 'Importar retornos CNAB',
  'reconciliation.read': 'Visualizar conciliação',
  'reconciliation.manage': 'Realizar conciliação',
  'notifications.read': 'Visualizar comunicações',
  'notifications.manage': 'Administrar comunicações',
  'integrations.read': 'Visualizar integrações',
  'integrations.manage': 'Administrar integrações personalizadas',
  'imports.read': 'Analisar importações',
  'imports.manage': 'Executar importações',
  'reports.read': 'Visualizar relatórios',
  'exports.read': 'Gerar exportações',
  'users.read': 'Visualizar usuários',
  'users.manage': 'Administrar usuários',
  'roles.read': 'Visualizar perfis de acesso',
  'roles.manage': 'Administrar perfis de acesso',
  'audit.read': 'Visualizar auditoria',
  '*': 'Acesso administrativo completo',
}

export function roleLabel(role?: string | null): string {
  if (!role) return 'Usuário'
  return roleLabels[role] || 'Usuário'
}

export function permissionLabel(permission: string): string {
  if (permissionLabels[permission]) return permissionLabels[permission]
  const normalized = permission
    .replace(/[._-]+/g, ' ')
    .replace(/\b\w/g, value => value.toUpperCase())
  return normalized || 'Permissão'
}

export function permissionGroup(permission: string): string {
  const prefix = permission.split('.')[0]
  const labels: Record<string, string> = {
    dashboard: 'Painel',
    companies: 'Empresas',
    customers: 'Clientes',
    services: 'Serviços',
    contracts: 'Contratos',
    receivables: 'Contas a receber',
    charges: 'Cobranças',
    payments: 'Pagamentos',
    banking: 'Bancos',
    cnab: 'CNAB',
    reconciliation: 'Conciliação',
    notifications: 'Comunicação',
    integrations: 'Integrações',
    imports: 'Importações',
    reports: 'Relatórios',
    exports: 'Exportações',
    users: 'Usuários',
    roles: 'Perfis de acesso',
    audit: 'Auditoria',
  }
  return labels[prefix] || 'Outras permissões'
}
