<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import {
  Activity, BadgeDollarSign, Bell, Building2, CircleDollarSign,
  FileArchive, FileCheck2, FileText, Gauge, Landmark, Link2, LogOut, Menu, MessageSquare, ReceiptText,
  Settings, ShieldCheck, Users, X
} from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { useAppStore } from '../stores/app'

const auth = useAuthStore()
const app = useAppStore()
const route = useRoute()
const router = useRouter()

const controlMenu = [
  { to: '/', label: 'Visão Geral', icon: Gauge },
  { to: '/tenants', label: 'Tenants', icon: Building2 },
  { to: '/platform-health', label: 'Operação', icon: Activity }
]
const tenantMenu = [
  { to: '/', label: 'Dashboard', icon: Gauge },
  { to: '/companies', label: 'Empresas', icon: Building2 },
  { to: '/customers', label: 'Clientes', icon: Users },
  { to: '/contracts', label: 'Contratos', icon: FileText },
  { to: '/receivables', label: 'Recebíveis', icon: CircleDollarSign },
  { to: '/charges', label: 'Cobranças', icon: ReceiptText },
  { to: '/banking', label: 'Bancos e CNAB', icon: Landmark },
  { to: '/reconciliation', label: 'Conciliação', icon: Link2 },
  { to: '/fiscal', label: 'Fiscal e recibos', icon: FileCheck2 },
  { to: '/integrations', label: 'Integrações', icon: Settings },
  { to: '/notifications', label: 'Comunicações', icon: MessageSquare },
  { to: '/imports', label: 'Importações', icon: FileArchive },
  { to: '/users', label: 'Usuários', icon: Users },
  { to: '/audit', label: 'Auditoria', icon: ShieldCheck }
]
const menu = computed(() => auth.isControlPlane ? controlMenu : tenantMenu)
const appName = computed(() => auth.isControlPlane ? 'ARGWS Control Plane' : app.tenant?.branding.name || 'Financeiro')

async function logout() { await auth.logout(); await router.push('/login') }
onMounted(() => { if (!auth.isControlPlane) app.loadTenantContext() })
</script>
<template>
  <div class="min-h-screen bg-slate-50">
    <div v-if="app.sidebarOpen" class="fixed inset-0 z-30 bg-slate-950/40 lg:hidden" @click="app.sidebarOpen = false" />
    <aside class="fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-slate-800 bg-slate-950 text-white transition-transform lg:translate-x-0" :class="app.sidebarOpen ? 'translate-x-0' : '-translate-x-full'">
      <div class="flex h-20 items-center gap-3 border-b border-slate-800 px-5">
        <div class="grid h-11 w-11 place-items-center rounded-2xl bg-teal-500/15 text-teal-300"><BadgeDollarSign :size="26" /></div>
        <div class="min-w-0"><p class="truncate text-sm font-bold">{{ appName }}</p><p class="text-xs text-slate-400">{{ auth.isControlPlane ? 'Administração SaaS' : 'Cobranças & Recebíveis' }}</p></div>
        <button class="ml-auto rounded-lg p-2 text-slate-400 hover:bg-slate-800 lg:hidden" @click="app.sidebarOpen = false"><X :size="20" /></button>
      </div>
      <nav class="flex-1 space-y-1 overflow-y-auto p-4">
        <RouterLink v-for="item in menu" :key="item.to" :to="item.to" class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition" :class="route.path === item.to ? 'bg-teal-500/15 text-teal-300' : 'text-slate-300 hover:bg-slate-900 hover:text-white'" @click="app.sidebarOpen = false">
          <component :is="item.icon" :size="19" />{{ item.label }}
        </RouterLink>
      </nav>
      <div class="border-t border-slate-800 p-4">
        <div class="mb-3 rounded-xl bg-slate-900 p-3"><p class="truncate text-sm font-semibold">{{ auth.user?.name }}</p><p class="truncate text-xs text-slate-400">{{ auth.user?.email }}</p></div>
        <button class="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-300 hover:bg-slate-900 hover:text-white" @click="logout"><LogOut :size="18" /> Sair</button>
      </div>
    </aside>
    <div class="lg:pl-72">
      <header class="sticky top-0 z-20 flex h-20 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-6 lg:px-8">
        <button class="rounded-xl border border-slate-200 p-2.5 text-slate-600 lg:hidden" @click="app.sidebarOpen = true"><Menu :size="20" /></button>
        <div class="hidden lg:block"><p class="text-xs font-medium uppercase tracking-wider text-slate-400">{{ auth.isControlPlane ? 'Control Plane' : app.tenant?.hostname }}</p></div>
        <div class="ml-auto flex items-center gap-2"><button class="rounded-xl border border-slate-200 p-2.5 text-slate-600 hover:bg-slate-50"><Bell :size="19" /></button></div>
      </header>
      <main class="p-4 sm:p-6 lg:p-8"><RouterView /></main>
    </div>
  </div>
</template>
