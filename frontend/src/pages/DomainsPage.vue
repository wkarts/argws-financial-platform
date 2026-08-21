<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { CheckCircle2, Globe2, RefreshCw, ShieldCheck, Star, Trash2 } from 'lucide-vue-next'
import { api, apiError } from '../api/client'
import type { ApiResponse } from '../types'
import PageHeader from '../components/PageHeader.vue'
import InlineAlert from '../components/InlineAlert.vue'
import StatusBadge from '../components/StatusBadge.vue'
import EmptyState from '../components/EmptyState.vue'

interface Domain { id:string;tenant_id:string;hostname:string;domain_type:string;status:string;is_primary:boolean;is_temporary:boolean;redirect_to_primary:boolean;ssl_status:string;dns_verified_at?:string;ssl_issued_at?:string;last_checked_at?:string;last_error?:string }
const items=ref<Domain[]>([]);const loading=ref(false);const error=ref('');const status=ref('')
async function load(){loading.value=true;error.value='';try{items.value=(await api.get<ApiResponse<Domain[]>>('/control/v1/domains',{params:{status:status.value||undefined}})).data.data}catch(e){error.value=apiError(e)}finally{loading.value=false}}
async function update(item:Domain,payload:Record<string,unknown>){try{await api.patch(`/control/v1/domains/${item.id}`,payload);await load()}catch(e){error.value=apiError(e)}}
async function verify(item:Domain){try{await api.post(`/control/v1/domains/${item.id}/verify`);await load()}catch(e){error.value=apiError(e)}}
async function remove(item:Domain){if(!confirm(`Remover o domínio ${item.hostname}?`))return;try{await api.delete(`/control/v1/domains/${item.id}`);await load()}catch(e){error.value=apiError(e)}}
onMounted(load)
</script>
<template>
<PageHeader title="Domínios e certificados" subtitle="Registro central de domínios provisionados e personalizados dos tenants."><select v-model="status" class="select w-44" @change="load"><option value="">Todos os status</option><option>PENDING</option><option>VERIFYING</option><option>ACTIVE</option><option>ERROR</option><option>SUSPENDED</option></select><button class="btn-secondary" @click="load"><RefreshCw :size="18" :class="loading&&'animate-spin'"/>Atualizar</button></PageHeader>
<InlineAlert :message="error" @dismiss="error=''"/>
<div class="table-wrap"><table class="table"><thead><tr><th>Domínio</th><th>Tenant</th><th>Tipo</th><th>DNS / SSL</th><th>Estado</th><th class="text-right">Ações</th></tr></thead><tbody><tr v-for="item in items" :key="item.id" class="border-t border-slate-100"><td><div class="flex items-center gap-2"><Globe2 :size="17" class="text-teal-600"/><span class="font-semibold">{{item.hostname}}</span><Star v-if="item.is_primary" :size="15" class="fill-amber-400 text-amber-400"/></div><p v-if="item.last_error" class="mt-1 max-w-md text-xs text-rose-600">{{item.last_error}}</p></td><td><RouterLink :to="`/tenants/${item.tenant_id}`" class="font-mono text-xs text-teal-700 hover:underline">{{item.tenant_id.slice(0,8)}}…</RouterLink></td><td><span class="badge bg-slate-100 text-slate-700">{{item.domain_type}}</span><p class="mt-1 text-xs text-slate-400">{{item.is_temporary?'Provisório':'Permanente'}}</p></td><td><div class="space-y-1 text-xs"><p class="flex items-center gap-1.5" :class="item.dns_verified_at?'text-emerald-700':'text-amber-700'"><CheckCircle2 :size="14"/>DNS {{item.dns_verified_at?'verificado':'pendente'}}</p><p class="flex items-center gap-1.5" :class="item.ssl_status==='ACTIVE'?'text-emerald-700':'text-amber-700'"><ShieldCheck :size="14"/>SSL {{item.ssl_status}}</p></div></td><td><StatusBadge :status="item.status"/></td><td><div class="flex justify-end gap-1"><button v-if="item.status!=='ACTIVE'" class="btn-secondary px-2.5 py-2" title="Verificar DNS" @click="verify(item)"><RefreshCw :size="16"/></button><button v-if="!item.is_primary" class="btn-secondary px-2.5 py-2" title="Definir principal" @click="update(item,{is_primary:true})"><Star :size="16"/></button><button class="btn-secondary px-2.5 py-2" :title="item.redirect_to_primary?'Desativar redirecionamento':'Redirecionar ao principal'" @click="update(item,{redirect_to_primary:!item.redirect_to_primary})"><Globe2 :size="16"/></button><button v-if="!item.is_temporary&&item.domain_type!=='PROVISIONED'&&!item.is_primary" class="btn-secondary px-2.5 py-2 text-rose-600" @click="remove(item)"><Trash2 :size="16"/></button></div></td></tr></tbody></table><EmptyState v-if="!items.length&&!loading" title="Nenhum domínio encontrado" description="Os domínios aparecerão após o provisionamento do primeiro tenant."/></div>
</template>
