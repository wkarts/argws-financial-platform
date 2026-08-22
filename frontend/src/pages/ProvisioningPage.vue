<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { CheckCircle2, Clock3, ExternalLink, Globe2, RefreshCw, ServerCog, TriangleAlert } from 'lucide-vue-next'
import { api, apiError } from '../api/client'
import type { Paginated, ProvisioningJob, ApiResponse, TenantDomain } from '../types'
import PageHeader from '../components/PageHeader.vue'
import PaginationBar from '../components/PaginationBar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import InlineAlert from '../components/InlineAlert.vue'
import DrawerPanel from '../components/DrawerPanel.vue'

const route = useRoute()
const jobs = ref<ProvisioningJob[]>([])
const domains = ref<Array<TenantDomain & { tenant_id: string }>>([])
const selected = ref<ProvisioningJob | null>(null)
const page = ref(1)
const pages = ref(1)
const status = ref('')
const loading = ref(false)
const error = ref('')
const lastUpdatedAt = ref<Date | null>(null)
const targetJobId = computed(() => typeof route.query.job === 'string' ? route.query.job : '')
const running = computed(() => jobs.value.filter(item => ['PENDING','RUNNING'].includes(item.status)).length)
const failed = computed(() => jobs.value.filter(item => item.status === 'FAILED').length)
const autoRefreshing = computed(() => running.value > 0 || Boolean(targetJobId.value && ['PENDING','RUNNING'].includes(selected.value?.status || '')))
let timer: ReturnType<typeof setInterval> | null = null

async function load(silent = false) {
  if (loading.value) return
  if (!silent) loading.value = true
  error.value = ''
  try {
    const [jobResponse, domainResponse] = await Promise.all([
      api.get<Paginated<ProvisioningJob>>('/control/v1/provisioning', { params: { page: page.value, per_page: 25, status: status.value || undefined } }),
      api.get<ApiResponse<Array<TenantDomain & { tenant_id: string }>>>('/control/v1/domains')
    ])
    jobs.value = jobResponse.data.data
    pages.value = jobResponse.data.meta.pages
    domains.value = domainResponse.data.data

    if (targetJobId.value) {
      const selectedResponse = await api.get<ApiResponse<ProvisioningJob>>(`/control/v1/provisioning/${targetJobId.value}`)
      selected.value = selectedResponse.data.data
    } else if (selected.value) {
      selected.value = jobs.value.find(item => item.id === selected.value?.id) || selected.value
    }
    lastUpdatedAt.value = new Date()
  } catch (exception) {
    error.value = apiError(exception)
  } finally {
    loading.value = false
  }
}

async function verifyDomain(id: string) {
  try {
    await api.post(`/control/v1/domains/${id}/verify`)
    await load()
  } catch (exception) {
    error.value = apiError(exception)
  }
}

function selectJob(item: ProvisioningJob) {
  selected.value = item
}

onMounted(async () => {
  await load()
  timer = setInterval(() => {
    if (autoRefreshing.value) void load(true)
  }, 2500)
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <PageHeader title="Provisionamento e domínios" subtitle="Banco, storage, DNS, bootstrap e validação de cada tenant com atualização automática.">
    <div class="mr-1 hidden items-center gap-1.5 text-xs text-slate-400 sm:flex"><span class="h-1.5 w-1.5 rounded-full" :class="autoRefreshing ? 'bg-emerald-500 animate-pulse' : 'bg-slate-300'" />{{ autoRefreshing ? 'acompanhando' : 'atualizado' }}</div>
    <button class="btn-primary" :disabled="loading" @click="load()"><RefreshCw :size="17" :class="loading && 'animate-spin'" /> Atualizar</button>
  </PageHeader>

  <InlineAlert v-if="error" tone="error" :message="error" class="mb-4" />

  <div class="mb-4 grid gap-3 sm:grid-cols-3">
    <div class="card"><div class="flex items-center gap-2.5"><ServerCog :size="20" class="text-blue-600" /><div><p class="text-[11px] uppercase text-slate-400">Jobs exibidos</p><p class="text-xl font-bold">{{ jobs.length }}</p></div></div></div>
    <div class="card"><div class="flex items-center gap-2.5"><Clock3 :size="20" class="text-amber-600" /><div><p class="text-[11px] uppercase text-slate-400">Em execução</p><p class="text-xl font-bold">{{ running }}</p></div></div></div>
    <div class="card"><div class="flex items-center gap-2.5"><TriangleAlert :size="20" class="text-rose-600" /><div><p class="text-[11px] uppercase text-slate-400">Falhas</p><p class="text-xl font-bold">{{ failed }}</p></div></div></div>
  </div>

  <div class="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
    <select v-model="status" class="select w-full sm:max-w-[220px]" @change="page=1; load()"><option value="">Todos os status</option><option>PENDING</option><option>RUNNING</option><option>SUCCEEDED</option><option>FAILED</option></select>
    <p v-if="lastUpdatedAt" class="text-xs text-slate-400">Última atualização: {{ lastUpdatedAt.toLocaleTimeString('pt-BR') }}</p>
  </div>

  <div class="table-wrap">
    <table class="table"><thead><tr><th>Tenant / operação</th><th>Etapa</th><th>Progresso</th><th>Status</th><th>Início</th><th></th></tr></thead><tbody>
      <tr v-for="item in jobs" :key="item.id" class="transition hover:bg-slate-50" :class="targetJobId === item.id ? 'bg-teal-50/70' : ''"><td><p class="max-w-[220px] truncate font-semibold">{{ item.tenant_id }}</p><p class="max-w-[240px] truncate text-xs text-slate-400">{{ item.operation }} · {{ item.correlation_id }}</p></td><td>{{ item.current_step }}</td><td><div class="w-36"><div class="h-1.5 rounded-full bg-slate-100"><div class="h-1.5 rounded-full bg-teal-600 transition-all" :style="{ width: `${Math.min(100, item.progress || 0)}%` }" /></div><p class="mt-1 text-[11px] text-slate-400">{{ item.progress || 0 }}% · {{ item.attempts }} tentativa(s)</p></div></td><td><StatusBadge :status="item.status" /></td><td>{{ item.started_at ? new Date(item.started_at).toLocaleString('pt-BR') : new Date(item.created_at).toLocaleString('pt-BR') }}</td><td><button class="btn-secondary !min-h-8 !px-2.5 !py-1.5" @click="selectJob(item)">Eventos</button></td></tr>
      <tr v-if="!jobs.length"><td colspan="6" class="py-10 text-center text-slate-400">Nenhum job encontrado.</td></tr>
    </tbody></table>
  </div>
  <PaginationBar v-model="page" :pages="pages" class="mt-4" @update:model-value="load" />

  <section class="mt-6">
    <div class="mb-3 flex items-center gap-2"><Globe2 :size="19" class="text-teal-700" /><h2 class="text-base font-semibold">Registry de domínios</h2></div>
    <div class="table-wrap"><table class="table"><thead><tr><th>Hostname</th><th>Tenant</th><th>Tipo</th><th>DNS</th><th>SSL</th><th></th></tr></thead><tbody>
      <tr v-for="domain in domains" :key="domain.id"><td><a :href="`https://${domain.hostname}`" target="_blank" class="inline-flex max-w-[280px] items-center gap-1.5 truncate font-semibold text-teal-700">{{ domain.hostname }}<ExternalLink :size="13" class="shrink-0" /></a></td><td class="max-w-[180px] truncate text-xs">{{ domain.tenant_id }}</td><td>{{ domain.domain_type }}<span v-if="domain.is_primary" class="badge ml-2 bg-blue-100 text-blue-700">Principal</span></td><td><StatusBadge :status="domain.status" /></td><td><StatusBadge :status="domain.ssl_status" /></td><td><button v-if="domain.domain_type === 'CUSTOM'" class="btn-secondary !min-h-8 !px-2.5 !py-1.5" @click="verifyDomain(domain.id)"><CheckCircle2 :size="14" /> Verificar</button><span v-else class="text-xs font-medium text-slate-400">Gerenciado</span></td></tr>
    </tbody></table></div>
  </section>

  <DrawerPanel :open="Boolean(selected)" title="Eventos do provisionamento" size="lg" @close="selected=null">
    <template v-if="selected">
      <div class="grid gap-2.5 sm:grid-cols-2"><div class="rounded-lg bg-slate-50 p-3"><p class="text-xs text-slate-400">Job</p><p class="break-all text-sm font-semibold">{{ selected.id }}</p></div><div class="rounded-lg bg-slate-50 p-3"><p class="text-xs text-slate-400">Status</p><StatusBadge class="mt-1.5" :status="selected.status" /></div></div>
      <div class="mt-3 rounded-lg bg-slate-50 p-3"><div class="mb-1.5 flex items-center justify-between text-xs"><span class="text-slate-500">{{ selected.current_step }}</span><span class="font-semibold">{{ selected.progress || 0 }}%</span></div><div class="h-2 rounded-full bg-slate-200"><div class="h-2 rounded-full bg-teal-600 transition-all" :style="{ width: `${Math.min(100, selected.progress || 0)}%` }" /></div></div>
      <p v-if="selected.last_error" class="mt-3 whitespace-pre-wrap rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{{ selected.last_error }}</p>
      <div class="mt-4 space-y-2.5"><article v-for="(event,index) in selected.events || []" :key="index" class="relative border-l-2 pl-3.5" :class="event.level === 'ERROR' ? 'border-rose-300' : 'border-teal-200'"><span class="absolute -left-[5px] top-1 h-2 w-2 rounded-full" :class="event.level === 'ERROR' ? 'bg-rose-500' : 'bg-teal-600'" /><p class="text-sm font-semibold">{{ event.step }}</p><p class="text-[13px] leading-5 text-slate-600">{{ event.message }}</p><p class="text-[11px] text-slate-400">{{ event.at ? new Date(event.at).toLocaleString('pt-BR') : '—' }}</p></article></div>
    </template>
  </DrawerPanel>
</template>
