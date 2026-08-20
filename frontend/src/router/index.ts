import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppLayout from '../layouts/AppLayout.vue'
import LoginPage from '../pages/LoginPage.vue'
import ControlDashboardPage from '../pages/ControlDashboardPage.vue'
import HomePage from '../pages/HomePage.vue'
import TenantsPage from '../pages/TenantsPage.vue'
import TenantDetailPage from '../pages/TenantDetailPage.vue'
import PlatformHealthPage from '../pages/PlatformHealthPage.vue'
import TenantDashboardPage from '../pages/TenantDashboardPage.vue'
import CompaniesPage from '../pages/CompaniesPage.vue'
import CustomersPage from '../pages/CustomersPage.vue'
import ContractsPage from '../pages/ContractsPage.vue'
import ReceivablesPage from '../pages/ReceivablesPage.vue'
import ChargesPage from '../pages/ChargesPage.vue'
import BankingPage from '../pages/BankingPage.vue'
import IntegrationsPage from '../pages/IntegrationsPage.vue'
import NotificationsPage from '../pages/NotificationsPage.vue'
import AuditPage from '../pages/AuditPage.vue'
import ReconciliationPage from '../pages/ReconciliationPage.vue'
import FiscalDocumentsPage from '../pages/FiscalDocumentsPage.vue'
import UsersPage from '../pages/UsersPage.vue'
import ImportsPage from '../pages/ImportsPage.vue'
import NotFoundPage from '../pages/NotFoundPage.vue'

const auth = () => useAuthStore()
const controlRoutes: RouteRecordRaw[] = [
  { path: 'tenants', component: TenantsPage },
  { path: 'tenants/:id', component: TenantDetailPage }, { path: 'platform-health', component: PlatformHealthPage }
]
const tenantRoutes: RouteRecordRaw[] = [
  { path: 'companies', component: CompaniesPage },
  { path: 'customers', component: CustomersPage }, { path: 'contracts', component: ContractsPage },
  { path: 'receivables', component: ReceivablesPage }, { path: 'charges', component: ChargesPage },
  { path: 'banking', component: BankingPage }, { path: 'reconciliation', component: ReconciliationPage },
  { path: 'fiscal', component: FiscalDocumentsPage }, { path: 'integrations', component: IntegrationsPage },
  { path: 'notifications', component: NotificationsPage }, { path: 'imports', component: ImportsPage }, { path: 'users', component: UsersPage }, { path: 'audit', component: AuditPage }
]
const routes: RouteRecordRaw[] = [
  { path: '/login', component: LoginPage, meta: { public: true } },
  { path: '/', component: AppLayout, children: [{ path: '', component: HomePage }, ...controlRoutes, ...tenantRoutes] },
  { path: '/:pathMatch(.*)*', component: NotFoundPage }
]
const router = createRouter({ history: createWebHistory(), routes })
router.beforeEach(to => {
  const store = auth(); if (!store.session) store.hydrate()
  if (!to.meta.public && !store.authenticated) return '/login'
  if (to.path === '/login' && store.authenticated) return '/'
  const controlOnly = ['/tenants','/platform-health'].some(p=>to.path.startsWith(p))
  const tenantOnly = ['/companies','/customers','/contracts','/receivables','/charges','/banking','/reconciliation','/fiscal','/integrations','/notifications','/imports','/users','/audit'].some(p=>to.path.startsWith(p))
  if (controlOnly && !store.isControlPlane) return '/'
  if (tenantOnly && store.isControlPlane) return '/'
})
export default router
