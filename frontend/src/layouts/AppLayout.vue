<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import {
  Activity, BadgeDollarSign, Banknote, Bell, Blocks, BriefcaseBusiness, Building2,
  ChevronDown, CircleDollarSign, CloudCog, Code2, DatabaseBackup, Download,
  FileArchive, FileCheck2, FileClock, FileSearch, FileText, Gauge, Globe2,
  KeyRound, Landmark, Link2, ListChecks, LogOut, Menu, MessageSquare, ReceiptText,
  RefreshCw, ScrollText, Settings, ShieldCheck, Sparkles, Tags, UploadCloud,
  UserCog, Users, WalletCards, X
} from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { useAppStore } from '../stores/app'

interface MenuItem { to: string; label: string; icon: unknown; badge?: string }
interface MenuGroup { label: string; items: MenuItem[] }

const auth = useAuthStore()
const app = useAppStore()
const route = useRoute()
const router = useRouter()
const notificationsOpen = ref(false)

const controlMenu: MenuGroup[] = [
  { label: 'Plataforma', items: [
    { to: '/', label: 'Visão geral', icon: Gauge },
    { to: '/tenants', label: 'Tenants', icon: Building2 },
    { to: '/plans', label: 'Planos e limites', icon: WalletCards },
    { to: '/platform-users', label: 'Equipe da plataforma', icon: Users }
  ] },
  { label: 'Infraestrutura', items: [
    { to: '/domains', label: 'Domínios e SSL', icon: Globe2 },
    { to: '/provisioning', label: 'Provisionamento', icon: CloudCog },
    { to: '/backups', label: 'Backup e restore', icon: DatabaseBackup },
    { to: '/platform-health', label: 'Saúde e filas', icon: Activity }
  ] },
  { label: 'Governança', items: [
    { to: '/platform-access', label: 'API e suporte', icon: KeyRound },
    { to: '/control-audit', label: 'Auditoria global', icon: ShieldCheck },
    { to: '/control-settings', label: 'Configurações', icon: Settings }
  ] }
]

const tenantMenu: MenuGroup[] = [
  { label: 'Visão geral', items: [
    { to: '/', label: 'Dashboard', icon: Gauge }
  ] },
  { label: 'Cadastros', items: [
    { to: '/companies', label: 'Empresas emissoras', icon: Building2 },
    { to: '/customers', label: 'Clientes e contatos', icon: Users },
    { to: '/services', label: 'Serviços', icon: Blocks },
    { to: '/contracts', label: 'Contratos e recorrência', icon: FileText }
  ] },
  { label: 'Cobrança e recebíveis', items: [
    { to: '/receivables', label: 'Contas a receber', icon: CircleDollarSign },
    { to: '/charges', label: 'Cobranças', icon: ReceiptText },
    { to: '/payments', label: 'Pagamentos', icon: Banknote },
    { to: '/payment-links', label: 'Links de pagamento', icon: Link2 },
    { to: '/negotiations', label: 'Negociações', icon: ListChecks }
  ] },
  { label: 'Bancos e conciliação', items: [
    { to: '/banking', label: 'Contas e convênios', icon: Landmark },
    { to: '/bank-transactions', label: 'Extratos e transações', icon: FileSearch },
    { to: '/cnab', label: 'CNAB 240/400', icon: ScrollText },
    { to: '/pix-automatic', label: 'Pix Automático', icon: Sparkles },
    { to: '/reconciliation', label: 'Conciliação', icon: Tags }
  ] },
  { label: 'Documentos e comunicação', items: [
    { to: '/fiscal', label: 'Fiscal e recibos', icon: FileCheck2 },
    { to: '/notifications', label: 'E-mail e WhatsApp', icon: MessageSquare },
    { to: '/documents', label: 'Central de documentos', icon: FileClock },
    { to: '/exports', label: 'Exportações', icon: Download },
    { to: '/reports', label: 'Relatórios', icon: FileArchive },
    { to: '/imports', label: 'Importações', icon: UploadCloud }
  ] },
  { label: 'Administração', items: [
    { to: '/integrations', label: 'Integrações operacionais', icon: Settings },
    { to: '/developer', label: 'API e webhooks', icon: Code2 },
    { to: '/roles', label: 'Perfis e permissões', icon: UserCog },
    { to: '/users', label: 'Usuários', icon: BriefcaseBusiness },
    { to: '/audit', label: 'Auditoria', icon: ShieldCheck }
  ] }
]

const groups = computed(() => auth.isControlPlane ? controlMenu : tenantMenu)
const appName = computed(() => auth.isControlPlane ? 'ARGWS Control Plane' : app.tenant?.branding.name || 'ARGWS Financeiro')
const planeLabel = computed(() => auth.isControlPlane ? 'Administração SaaS' : 'Cobranças & Recebíveis')
const currentTitle = computed(() => {
  for (const group of groups.value) {
    const item = group.items.find(value => isActive(value.to))
    if (item) return item.label
  }
  return auth.isControlPlane ? 'Control Plane' : app.tenant?.hostname || 'Financeiro'
})

function isActive(to: string): boolean {
  if (to === '/') return route.path === '/'
  return route.path === to || route.path.startsWith(`${to}/`)
}

async function logout() {
  await auth.logout()
  await router.push('/login')
}

async function refreshContext() {
  if (!auth.isControlPlane) await app.loadTenantContext()
}

onMounted(refreshContext)
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <div v-if="app.sidebarOpen" class="fixed inset-0 z-30 bg-slate-950/50 backdrop-blur-sm lg:hidden" @click="app.sidebarOpen = false" />

    <aside class="fixed inset-y-0 left-0 z-40 flex w-64 max-w-[86vw] flex-col border-r border-slate-800 bg-slate-950 text-white transition-transform duration-200 lg:translate-x-0" :class="app.sidebarOpen ? 'translate-x-0' : '-translate-x-full'">
      <div class="flex h-16 items-center gap-2.5 border-b border-slate-800 px-4">
        <div class="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-teal-500/15 text-teal-300"><BadgeDollarSign :size="22" /></div>
        <div class="min-w-0"><p class="truncate text-[13px] font-bold">{{ appName }}</p><p class="truncate text-[11px] text-slate-400">{{ planeLabel }}</p></div>
        <button class="ml-auto rounded-lg p-2 text-slate-400 hover:bg-slate-800 lg:hidden" aria-label="Fechar menu" @click="app.sidebarOpen = false"><X :size="18" /></button>
      </div>

      <nav class="flex-1 overflow-y-auto p-3">
        <section v-for="group in groups" :key="group.label" class="mb-4">
          <p class="mb-1.5 px-2.5 text-[9px] font-bold uppercase tracking-[0.16em] text-slate-500">{{ group.label }}</p>
          <div class="space-y-0.5">
            <RouterLink v-for="item in group.items" :key="item.to" :to="item.to" class="flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium transition" :class="isActive(item.to) ? 'bg-teal-500/15 text-teal-300 shadow-inner' : 'text-slate-300 hover:bg-slate-900 hover:text-white'" @click="app.sidebarOpen = false">
              <component :is="item.icon" :size="17" /><span class="min-w-0 flex-1 truncate">{{ item.label }}</span><span v-if="item.badge" class="rounded-full bg-slate-800 px-2 py-0.5 text-[9px]">{{ item.badge }}</span>
            </RouterLink>
          </div>
        </section>
      </nav>

      <div class="border-t border-slate-800 p-3">
        <div class="mb-2 rounded-lg bg-slate-900 p-2.5">
          <p class="truncate text-[13px] font-semibold">{{ auth.user?.name }}</p>
          <p class="truncate text-[11px] text-slate-400">{{ auth.user?.email }}</p>
          <p class="mt-1.5 inline-flex rounded-full bg-slate-800 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-slate-300">{{ auth.user?.role }}</p>
        </div>
        <button class="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] text-slate-300 hover:bg-slate-900 hover:text-white" @click="logout"><LogOut :size="17" /> Sair</button>
      </div>
    </aside>

    <div class="min-w-0 lg:pl-64">
      <header class="sticky top-0 z-20 flex h-16 items-center border-b border-slate-200 bg-white/95 px-3 backdrop-blur sm:px-4 lg:px-6">
        <button class="rounded-lg border border-slate-200 p-2 text-slate-600 lg:hidden" aria-label="Abrir menu" @click="app.sidebarOpen = true"><Menu :size="19" /></button>
        <div class="ml-2.5 min-w-0 lg:ml-0">
          <p class="truncate text-[13px] font-semibold text-slate-900">{{ currentTitle }}</p>
          <p class="truncate text-[11px] text-slate-400">{{ auth.isControlPlane ? 'control plane isolado' : app.tenant?.hostname || 'tenant plane' }}</p>
        </div>
        <div class="ml-auto flex items-center gap-1.5">
          <button v-if="!auth.isControlPlane" class="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50" title="Atualizar contexto" @click="refreshContext"><RefreshCw :size="17" /></button>
          <div class="relative">
            <button class="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50" aria-label="Notificações" @click="notificationsOpen = !notificationsOpen"><Bell :size="18" /></button>
            <div v-if="notificationsOpen" class="absolute right-0 mt-2 w-[min(19rem,calc(100vw-1.5rem))] rounded-xl border border-slate-200 bg-white p-3.5 shadow-xl">
              <div class="flex items-center justify-between"><p class="text-sm font-semibold">Central operacional</p><ChevronDown :size="15" class="text-slate-400" /></div>
              <p class="mt-2 text-[13px] leading-5 text-slate-500">Alertas de cobrança, integrações, filas, domínios e backups aparecem nos respectivos painéis operacionais.</p>
            </div>
          </div>
        </div>
      </header>
      <main class="min-w-0 p-3 sm:p-4 lg:p-6"><RouterView /></main>
    </div>
  </div>
</template>
