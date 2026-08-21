import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppLayout from '../layouts/AppLayout.vue'
import LoginPage from '../pages/LoginPage.vue'
import NotFoundPage from '../pages/NotFoundPage.vue'
import PublicPaymentPage from '../pages/PublicPaymentPage.vue'

// Control Plane
import ControlDashboardPage from '../pages/ControlDashboardPage.vue'
import TenantsPage from '../pages/TenantsPage.vue'
import TenantDetailPage from '../pages/TenantDetailPage.vue'
import PlansPage from '../pages/PlansPage.vue'
import PlatformUsersPage from '../pages/PlatformUsersPage.vue'
import DomainsPage from '../pages/DomainsPage.vue'
import ProvisioningPage from '../pages/ProvisioningPage.vue'
import BackupsPage from '../pages/BackupsPage.vue'
import PlatformHealthPage from '../pages/PlatformHealthPage.vue'
import PlatformAccessPage from '../pages/PlatformAccessPage.vue'
import ControlAuditPage from '../pages/ControlAuditPage.vue'
import ControlSettingsPage from '../pages/ControlSettingsPage.vue'

// Tenant Plane
import TenantDashboardPage from '../pages/TenantDashboardPage.vue'
import CompaniesPage from '../pages/CompaniesPage.vue'
import CustomersPage from '../pages/CustomersPage.vue'
import ServicesPage from '../pages/ServicesPage.vue'
import ContractsPage from '../pages/ContractsPage.vue'
import ReceivablesPage from '../pages/ReceivablesPage.vue'
import ChargesPage from '../pages/ChargesPage.vue'
import PaymentsPage from '../pages/PaymentsPage.vue'
import PaymentLinksPage from '../pages/PaymentLinksPage.vue'
import NegotiationsPage from '../pages/NegotiationsPage.vue'
import BankingPage from '../pages/BankingPage.vue'
import BankTransactionsPage from '../pages/BankTransactionsPage.vue'
import CNABPage from '../pages/CNABPage.vue'
import PixAutomaticPage from '../pages/PixAutomaticPage.vue'
import ReconciliationPage from '../pages/ReconciliationPage.vue'
import FiscalDocumentsPage from '../pages/FiscalDocumentsPage.vue'
import NotificationsPage from '../pages/NotificationsPage.vue'
import DocumentsPage from '../pages/DocumentsPage.vue'
import ExportsPage from '../pages/ExportsPage.vue'
import ReportsPage from '../pages/ReportsPage.vue'
import ImportsPage from '../pages/ImportsPage.vue'
import IntegrationsPage from '../pages/IntegrationsPage.vue'
import DeveloperIntegrationsPage from '../pages/DeveloperIntegrationsPage.vue'
import RolesPage from '../pages/RolesPage.vue'
import UsersPage from '../pages/UsersPage.vue'
import AuditPage from '../pages/AuditPage.vue'

const controlMeta = { plane: 'control' as const }
const tenantMeta = { plane: 'tenant' as const }

const controlRoutes: RouteRecordRaw[] = [
  { path: '', name: 'control-dashboard', component: ControlDashboardPage, meta: controlMeta },
  { path: 'tenants', name: 'tenants', component: TenantsPage, meta: controlMeta },
  { path: 'tenants/:id', name: 'tenant-detail', component: TenantDetailPage, meta: controlMeta },
  { path: 'plans', name: 'plans', component: PlansPage, meta: controlMeta },
  { path: 'platform-users', name: 'platform-users', component: PlatformUsersPage, meta: controlMeta },
  { path: 'domains', name: 'domains', component: DomainsPage, meta: controlMeta },
  { path: 'provisioning', name: 'provisioning', component: ProvisioningPage, meta: controlMeta },
  { path: 'backups', name: 'backups', component: BackupsPage, meta: controlMeta },
  { path: 'platform-health', name: 'platform-health', component: PlatformHealthPage, meta: controlMeta },
  { path: 'platform-access', name: 'platform-access', component: PlatformAccessPage, meta: controlMeta },
  { path: 'control-audit', name: 'control-audit', component: ControlAuditPage, meta: controlMeta },
  { path: 'control-settings', name: 'control-settings', component: ControlSettingsPage, meta: controlMeta },
  // Compatibilidade com URLs de versões alpha anteriores.
  { path: 'support', redirect: '/platform-access' },
  { path: 'platform-api-keys', redirect: '/platform-access' }
]

const tenantRoutes: RouteRecordRaw[] = [
  { path: '', name: 'tenant-dashboard', component: TenantDashboardPage, meta: tenantMeta },
  { path: 'companies', name: 'companies', component: CompaniesPage, meta: tenantMeta },
  { path: 'customers', name: 'customers', component: CustomersPage, meta: tenantMeta },
  { path: 'services', name: 'services', component: ServicesPage, meta: tenantMeta },
  { path: 'contracts', name: 'contracts', component: ContractsPage, meta: tenantMeta },
  { path: 'receivables', name: 'receivables', component: ReceivablesPage, meta: tenantMeta },
  { path: 'charges', name: 'charges', component: ChargesPage, meta: tenantMeta },
  { path: 'payments', name: 'payments', component: PaymentsPage, meta: tenantMeta },
  { path: 'payment-links', name: 'payment-links', component: PaymentLinksPage, meta: tenantMeta },
  { path: 'negotiations', name: 'negotiations', component: NegotiationsPage, meta: tenantMeta },
  { path: 'banking', name: 'banking', component: BankingPage, meta: tenantMeta },
  { path: 'bank-transactions', name: 'bank-transactions', component: BankTransactionsPage, meta: tenantMeta },
  { path: 'cnab', name: 'cnab', component: CNABPage, meta: tenantMeta },
  { path: 'pix-automatic', name: 'pix-automatic', component: PixAutomaticPage, meta: tenantMeta },
  { path: 'reconciliation', name: 'reconciliation', component: ReconciliationPage, meta: tenantMeta },
  { path: 'fiscal', name: 'fiscal', component: FiscalDocumentsPage, meta: tenantMeta },
  { path: 'notifications', name: 'notifications', component: NotificationsPage, meta: tenantMeta },
  { path: 'documents', name: 'documents', component: DocumentsPage, meta: tenantMeta },
  { path: 'exports', name: 'exports', component: ExportsPage, meta: tenantMeta },
  { path: 'reports', name: 'reports', component: ReportsPage, meta: tenantMeta },
  { path: 'imports', name: 'imports', component: ImportsPage, meta: tenantMeta },
  { path: 'integrations', name: 'integrations', component: IntegrationsPage, meta: tenantMeta },
  { path: 'developer', name: 'developer', component: DeveloperIntegrationsPage, meta: tenantMeta },
  { path: 'roles', name: 'roles', component: RolesPage, meta: tenantMeta },
  { path: 'users', name: 'users', component: UsersPage, meta: tenantMeta },
  { path: 'audit', name: 'audit', component: AuditPage, meta: tenantMeta }
]

const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'login', component: LoginPage, meta: { public: true } },
  { path: '/p/:token', name: 'public-payment', component: PublicPaymentPage, meta: { public: true } },
  {
    path: '/',
    component: AppLayout,
    children: [...controlRoutes, ...tenantRoutes]
  },
  { path: '/:pathMatch(.*)*', component: NotFoundPage, meta: { public: true } }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(to => {
  const auth = useAuthStore()
  if (!auth.session) auth.hydrate()

  if (!to.meta.public && !auth.authenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.authenticated) return { path: '/' }
  if (to.meta.plane === 'control' && !auth.isControlPlane) return { path: '/' }
  if (to.meta.plane === 'tenant' && auth.isControlPlane) return { path: '/' }
  return true
})

export default router
