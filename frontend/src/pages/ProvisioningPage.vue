<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CheckCircle2, Clock3, ExternalLink, Globe2, RefreshCw, ServerCog, TriangleAlert } from 'lucide-vue-next'
import { api, apiError } from '../api/client'
import type { Paginated, ProvisioningJob, ApiResponse, TenantDomain } from '../types'
import PageHeader from '../components/PageHeader.vue'
import PaginationBar from '../components/PaginationBar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import InlineAlert from '../components/InlineAlert.vue'
import DrawerPanel from '../components/DrawerPanel.vue'

const jobs = ref<ProvisioningJob[]>([])
const domains = ref<Array<TenantDomain & { tenant_id: string }>>([])
const selected = ref<ProvisioningJob | null>(null)
const page = ref(1)
const pages = ref(1)
const status = ref('')
const loading = ref(false)
const error = ref('')
const running = computed(() => jobs.value.filter(item => ['PENDING','RUNNING'].includes(item.status)).length)
const failed = computed(() => jobs.value.filter(item => item.status === 'FAILED').length)

async function load() {
  loading.value = true; error.value = ''
  try {
    const [jobResponse, domainResponse] = await Promise.all([
      api.get<Paginated<ProvisioningJob>>('/control/v1/provisioning', { params: { page: page.value, per_page: 25, status: status.value || undefined } }),
      api.get<ApiResponse<Array<TenantDomain & { tenant_id: string }>>>('/control/v1/domains')
    ])
    jobs.value = jobResponse.data.data; pages.value = jobResponse.data.meta.pages; domains.value = domainResponse.data.data
  } catch (exception) { error.value = apiError(exception) } finally { loading.value = false }
}

async function verifyDomain(id: string) {
  try { await api.post(`/control/v1/domains/${id}/verify`); await load() } catch (exception) { error.value = apiError(exception) }
}

onMounted(load)
</script>

<template>
  <PageHeader title="Provisionamento e domínios" subtitle="Acompanhe banco, storage, DNS, SSL, bootstrap e smoke tests de cada tenant.">
    <button class="btn-primary" :disabled="loading" @click="load"><RefreshCw :size="18" :class="loading && 'animate-spin'" /> Atualizar</button>
  </PageHeader>
  <InlineAlert v-if="error" tone="error" :message="error" class="mb-5" />

  <div class="mb-6 grid gap-4 sm:grid-cols-3">
    <div class="card"><div class="flex items-center gap-3"><ServerCog class="text-blue-600" /><div><p class="text-xs uppercase text-slate-400">Jobs exibidos</p><p class="text-2xl font-bold">{{ jobs.length }}</p></div></div></div>
    <div class="card"><div class="flex items-center gap-3"><Clock3 class="text-amber-600" /><div><p class="text-xs uppercase text-slate-400">Em execução</p><p class="text-2xl font-bold">{{ running }}</p></div></div></div>
    <div class="card"><div class="flex items-center gap-3"><TriangleAlert class="text-rose-600" /><div><p class="text-xs uppercase text-slate-400">Falhas</p><p class="text-2xl font-bold">{{ failed }}</p></div></div></div>
  </div>

  <div class="mb-5 flex flex-wrap gap-2"><select v-model="status" class="select max-w-xs" @change="page=1; load()"><option value="">Todos os status</option><option>PENDING</option><option>RUNNING</option><option>SUCCEEDED</option><option>FAILED</option></select></div>
  <div class="table-wrap">
    <table class="table"><thead><tr><th>Tenant / operação</th><th>Etapa</th><th>Progresso</th><th>Status</th><th>Início</th><th></th></tr></thead><tbody>
      <tr v-for="item in jobs" :key="item.id"><td><p class="font-semibold">{{ item.tenant_id }}</p><p class="text-xs text-slate-400">{{ item.operation }} · {{ item.correlation_id }}</p></td><td>{{ item.current_step }}</td><td><div class="w-40"><div class="h-2 rounded-full bg-slate-100"><div class="h-2 rounded-full bg-teal-600" :style="{ width: `${Math.min(100, item.progress || 0)}%` }" /></div><p class="mt-1 text-xs text-slate-400">{{ item.progress || 0 }}% · {{ item.attempts }} tentativa(s)</p></div></td><td><StatusBadge :status="item.status" /></td><td>{{ item.started_at ? new Date(item.started_at).toLocaleString('pt-BR') : new Date(item.created_at).toLocaleString('pt-BR') }}</td><td><button class="btn-secondary !px-3 !py-2" @click="selected=item">Eventos</button></td></tr>
      <tr v-if="!jobs.length"><td colspan="6" class="py-12 text-center text-slate-400">Nenhum job encontrado.</td></tr>
    </tbody></table>
  </div>
  <PaginationBar v-model="page" :pages="pages" class="mt-5" @update:model-value="load" />

  <section class="mt-8">
    <div class="mb-4 flex items-center gap-2"><Globe2 :size="21" class="text-teal-700" /><h2 class="text-lg font-semibold">Registry de domínios</h2></div>
    <div class="table-wrap"><table class="table"><thead><tr><th>Hostname</th><th>Tenant</th><th>Tipo</th><th>DNS</th><th>SSL</th><th></th></tr></thead><tbody>
      <tr v-for="domain in domains" :key="domain.id"><td><a :href="`https://${domain.hostname}`" target="_blank" class="inline-flex items-center gap-2 font-semibold text-teal-700">{{ domain.hostname }}<ExternalLink :size="14" /></a></td><td class="text-xs">{{ domain.tenant_id }}</td><td>{{ domain.domain_type }}<span v-if="domain.is_primary" class="badge ml-2 bg-blue-100 text-blue-700">Principal</span></td><td><StatusBadge :status="domain.status" /></td><td><StatusBadge :status="domain.ssl_status" /></td><td><button class="btn-secondary !px-3 !py-2" @click="verifyDomain(domain.id)"><CheckCircle2 :size="15" /> Verificar</button></td></tr>
    </tbody></table></div>
  </section>

  <DrawerPanel :open="Boolean(selected)" title="Eventos do provisionamento" size="lg" @close="selected=null">
    <template v-if="selected">
      <div class="grid gap-3 sm:grid-cols-2"><div class="rounded-xl bg-slate-50 p-3"><p class="text-xs text-slate-400">Job</p><p class="break-all text-sm font-semibold">{{ selected.id }}</p></div><div class="rounded-xl bg-slate-50 p-3"><p class="text-xs text-slate-400">Status</p><StatusBadge class="mt-2" :status="selected.status" /></div></div>
      <p v-if="selected.last_error" class="mt-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{{ selected.last_error }}</p>
      <div class="mt-5 space-y-3"><article v-for="(event,index) in selected.events || []" :key="index" class="relative border-l-2 border-teal-200 pl-4"><span class="absolute -left-[5px] top-1 h-2 w-2 rounded-full bg-teal-600" /><p class="text-sm font-semibold">{{ event.step }}</p><p class="text-sm text-slate-600">{{ event.message }}</p><p class="text-xs text-slate-400">{{ event.at ? new Date(event.at).toLocaleString('pt-BR') : '—' }}</p></article></div>
    </template>
  </DrawerPanel>
</template>
