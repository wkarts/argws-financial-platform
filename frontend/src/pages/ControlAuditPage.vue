<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Download, Search, ShieldCheck } from 'lucide-vue-next'
import { api, apiError } from '../api/client'
import type { Paginated } from '../types'
import PageHeader from '../components/PageHeader.vue'
import PaginationBar from '../components/PaginationBar.vue'
import InlineAlert from '../components/InlineAlert.vue'

interface AuditItem { id:string; actor_id?:string; tenant_id?:string; action:string; entity_type:string; entity_id?:string; before:Record<string,unknown>; after:Record<string,unknown>; context:Record<string,unknown>; correlation_id?:string; created_at:string }
const items=ref<AuditItem[]>([]); const page=ref(1); const pages=ref(1); const action=ref(''); const tenant=ref(''); const error=ref('')
async function load(){try{const response=await api.get<Paginated<AuditItem>>('/control/v1/audit',{params:{page:page.value,per_page:100,action:action.value||undefined,tenant_id:tenant.value||undefined}});items.value=response.data.data;pages.value=response.data.meta.pages}catch(e){error.value=apiError(e)}}
function exportCsv(){const q=(v:unknown)=>`"${String(v??'').replaceAll('"','""')}"`;const lines=['data;acao;entidade;entidade_id;ator;tenant;correlation_id',...items.value.map(i=>[i.created_at,i.action,i.entity_type,i.entity_id,i.actor_id,i.tenant_id,i.correlation_id].map(q).join(';'))];const blob=new Blob([`\uFEFF${lines.join('\n')}`],{type:'text/csv'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='auditoria-control-plane.csv';a.click();URL.revokeObjectURL(a.href)}
onMounted(load)
</script>
<template>
<PageHeader title="Auditoria global" subtitle="Trilha imutável das operações do Control Plane, provisionamento e suporte."><button class="btn-secondary" @click="exportCsv"><Download :size="18"/> Exportar</button></PageHeader>
<InlineAlert v-if="error" tone="error" :message="error" class="mb-5"/>
<div class="mb-5 grid gap-3 md:grid-cols-[1fr_1fr_auto]"><div class="relative"><Search class="absolute left-3 top-3 text-slate-400" :size="18"/><input v-model="action" class="input pl-10" placeholder="Ação" @keyup.enter="page=1;load()"/></div><input v-model="tenant" class="input" placeholder="UUID do tenant" @keyup.enter="page=1;load()"/><button class="btn-primary" @click="page=1;load()">Pesquisar</button></div>
<div class="table-wrap"><table class="table"><thead><tr><th>Data</th><th>Ação</th><th>Entidade</th><th>Ator / Tenant</th><th>Alterações</th></tr></thead><tbody><tr v-for="item in items" :key="item.id"><td class="whitespace-nowrap">{{new Date(item.created_at).toLocaleString('pt-BR')}}</td><td><span class="inline-flex items-center gap-2 font-semibold"><ShieldCheck :size="16" class="text-teal-700"/>{{item.action}}</span><p class="text-xs text-slate-400">{{item.correlation_id||'—'}}</p></td><td>{{item.entity_type}}<p class="max-w-xs truncate text-xs text-slate-400">{{item.entity_id||'—'}}</p></td><td><p class="max-w-xs truncate text-xs">{{item.actor_id||'Sistema'}}</p><p class="max-w-xs truncate text-xs text-slate-400">{{item.tenant_id||'Plataforma'}}</p></td><td><details><summary class="cursor-pointer text-xs font-semibold text-teal-700">Comparar JSON</summary><div class="mt-2 grid gap-2 lg:grid-cols-2"><pre class="max-h-52 overflow-auto rounded-xl bg-slate-950 p-3 text-[10px] text-rose-300">{{JSON.stringify(item.before||{},null,2)}}</pre><pre class="max-h-52 overflow-auto rounded-xl bg-slate-950 p-3 text-[10px] text-emerald-300">{{JSON.stringify(item.after||{},null,2)}}</pre></div></details></td></tr><tr v-if="!items.length"><td colspan="5" class="py-12 text-center text-slate-400">Nenhum evento encontrado.</td></tr></tbody></table></div>
<PaginationBar v-model="page" :pages="pages" class="mt-5" @update:model-value="load"/>
</template>
