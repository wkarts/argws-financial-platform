<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Globe2, Plus, RefreshCw, RotateCcw } from 'lucide-vue-next'
import { api, apiError } from '../api/client'
import type { ApiResponse, Tenant } from '../types'
import PageHeader from '../components/PageHeader.vue'
import StatusBadge from '../components/StatusBadge.vue'
import ModalDialog from '../components/ModalDialog.vue'

const route = useRoute()
const router = useRouter()
const tenant = ref<Tenant | null>(null)
const error = ref('')
const modal = ref(false)
const hostname = ref('')
const primary = ref(false)
const retrying = ref(false)

async function load() {
  error.value = ''
  try {
    tenant.value = (await api.get<ApiResponse<Tenant>>(`/control/v1/tenants/${route.params.id}`)).data.data
  } catch (e) {
    error.value = apiError(e)
  }
}

async function addDomain() {
  try {
    await api.post(`/control/v1/tenants/${route.params.id}/domains`, { hostname: hostname.value, is_primary: primary.value })
    modal.value = false
    hostname.value = ''
    await load()
  } catch (e) {
    error.value = apiError(e)
  }
}

async function verify(id: string) {
  try {
    await api.post(`/control/v1/domains/${id}/verify`)
    await load()
  } catch (e) {
    error.value = apiError(e)
  }
}

async function retry() {
  if (retrying.value) return
  retrying.value = true
  error.value = ''
  try {
    const response = await api.post<ApiResponse<{ job_id: string; status: string }>>(`/control/v1/tenants/${route.params.id}/provision`)
    await router.push({ path: '/provisioning', query: { job: response.data.data.job_id, tenant: String(route.params.id) } })
  } catch (e) {
    error.value = apiError(e)
  } finally {
    retrying.value = false
  }
}

onMounted(load)
</script>

<template>
  <PageHeader :title="tenant?.name || 'Tenant'" :subtitle="tenant ? `${tenant.slug} · ${tenant.plan_code}` : 'Carregando…'">
    <button class="btn-secondary" :disabled="retrying" @click="retry"><RotateCcw :size="17" :class="retrying && 'animate-spin'" /> {{ retrying ? 'Reprocessando…' : 'Reprocessar' }}</button>
    <button class="btn-primary" @click="modal=true"><Plus :size="17" /> Domínio</button>
  </PageHeader>

  <p v-if="error" class="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{{ error }}</p>

  <template v-if="tenant">
    <div class="grid gap-3 sm:grid-cols-3">
      <div class="card"><p class="text-xs text-slate-500">Status</p><div class="mt-2"><StatusBadge :status="tenant.status" /></div></div>
      <div class="card"><p class="text-xs text-slate-500">Timezone</p><p class="mt-2 text-sm font-semibold">{{ tenant.timezone }}</p></div>
      <div class="card"><p class="text-xs text-slate-500">Criado</p><p class="mt-2 text-sm font-semibold">{{ new Date(tenant.created_at).toLocaleString('pt-BR') }}</p></div>
    </div>

    <section class="mt-5">
      <h2 class="mb-2.5 text-base font-semibold">Domínios</h2>
      <div class="table-wrap"><table class="table"><thead><tr><th>Hostname</th><th>Tipo</th><th>DNS</th><th>SSL</th><th></th></tr></thead><tbody><tr v-for="domain in tenant.domains" :key="domain.id"><td><div class="flex items-center gap-2"><Globe2 :size="15" class="shrink-0 text-slate-400"/><span class="max-w-[280px] truncate font-medium">{{ domain.hostname }}</span><span v-if="domain.is_primary" class="badge bg-blue-100 text-blue-700">Principal</span></div></td><td>{{ domain.domain_type }}</td><td><StatusBadge :status="domain.status" /></td><td><StatusBadge :status="domain.ssl_status" /></td><td><button v-if="domain.domain_type === 'CUSTOM'" class="btn-secondary !min-h-8 !px-2.5 !py-1.5" @click="verify(domain.id)"><RefreshCw :size="14"/> Verificar</button><span v-else class="text-xs font-medium text-slate-400">Gerenciado</span></td></tr></tbody></table></div>
    </section>
  </template>

  <ModalDialog :open="modal" title="Adicionar domínio personalizado" @close="modal=false">
    <form class="space-y-3" @submit.prevent="addDomain">
      <div><label class="label">Hostname completo</label><input v-model="hostname" class="input" placeholder="financeiro.cliente.com.br" required /><p class="mt-1.5 text-xs leading-5 text-slate-500">Configure um CNAME apontando para o gateway informado pela plataforma.</p></div>
      <label class="flex items-center gap-2 text-sm"><input v-model="primary" type="checkbox"/> Tornar domínio principal</label>
      <div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end"><button type="button" class="btn-secondary" @click="modal=false">Cancelar</button><button class="btn-primary">Cadastrar</button></div>
    </form>
  </ModalDialog>
</template>
