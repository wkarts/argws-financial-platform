<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Globe2, Plus, RefreshCw, RotateCcw } from 'lucide-vue-next'
import { api, apiError } from '../api/client'
import type { ApiResponse, Tenant } from '../types'
import PageHeader from '../components/PageHeader.vue'
import StatusBadge from '../components/StatusBadge.vue'
import ModalDialog from '../components/ModalDialog.vue'

const route = useRoute(); const tenant = ref<Tenant | null>(null); const error = ref(''); const modal=ref(false); const hostname=ref(''); const primary=ref(false)
async function load(){ try{ tenant.value=(await api.get<ApiResponse<Tenant>>(`/control/v1/tenants/${route.params.id}`)).data.data }catch(e){error.value=apiError(e)} }
async function addDomain(){try{await api.post(`/control/v1/tenants/${route.params.id}/domains`,{hostname:hostname.value,is_primary:primary.value});modal.value=false;hostname.value='';await load()}catch(e){error.value=apiError(e)}}
async function verify(id:string){try{await api.post(`/control/v1/domains/${id}/verify`);await load()}catch(e){error.value=apiError(e)}}
async function retry(){try{await api.post(`/control/v1/tenants/${route.params.id}/provision`);await load()}catch(e){error.value=apiError(e)}}
onMounted(load)
</script>
<template>
  <PageHeader :title="tenant?.name || 'Tenant'" :subtitle="tenant ? `${tenant.slug} · ${tenant.plan_code}` : 'Carregando…'"><button class="btn-secondary" @click="retry"><RotateCcw :size="18" /> Reprocessar</button><button class="btn-primary" @click="modal=true"><Plus :size="18" /> Domínio</button></PageHeader>
  <p v-if="error" class="mb-5 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{{ error }}</p>
  <template v-if="tenant"><div class="grid gap-4 sm:grid-cols-3"><div class="card"><p class="text-sm text-slate-500">Status</p><div class="mt-3"><StatusBadge :status="tenant.status" /></div></div><div class="card"><p class="text-sm text-slate-500">Timezone</p><p class="mt-3 font-semibold">{{tenant.timezone}}</p></div><div class="card"><p class="text-sm text-slate-500">Criado</p><p class="mt-3 font-semibold">{{new Date(tenant.created_at).toLocaleString('pt-BR')}}</p></div></div>
  <section class="mt-6"><h2 class="mb-3 text-lg font-semibold">Domínios</h2><div class="table-wrap"><table class="table"><thead><tr><th>Hostname</th><th>Tipo</th><th>DNS</th><th>SSL</th><th></th></tr></thead><tbody><tr v-for="domain in tenant.domains" :key="domain.id"><td><div class="flex items-center gap-2"><Globe2 :size="16" class="text-slate-400"/><span class="font-medium">{{domain.hostname}}</span><span v-if="domain.is_primary" class="badge bg-blue-100 text-blue-700">Principal</span></div></td><td>{{domain.domain_type}}</td><td><StatusBadge :status="domain.status" /></td><td><StatusBadge :status="domain.ssl_status" /></td><td><button v-if="domain.domain_type==='CUSTOM'" class="btn-secondary py-1.5" @click="verify(domain.id)"><RefreshCw :size="15"/> Verificar</button></td></tr></tbody></table></div></section></template>
  <ModalDialog :open="modal" title="Adicionar domínio personalizado" @close="modal=false"><form class="space-y-4" @submit.prevent="addDomain"><div><label class="label">Hostname completo</label><input v-model="hostname" class="input" placeholder="financeiro.cliente.com.br" required /><p class="mt-2 text-xs text-slate-500">Configure um CNAME apontando para o gateway informado pela plataforma.</p></div><label class="flex items-center gap-2 text-sm"><input v-model="primary" type="checkbox"/> Tornar domínio principal</label><div class="flex justify-end gap-2"><button type="button" class="btn-secondary" @click="modal=false">Cancelar</button><button class="btn-primary">Cadastrar</button></div></form></ModalDialog>
</template>
