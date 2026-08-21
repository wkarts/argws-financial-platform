<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Download, RefreshCw, Search, ShieldCheck } from 'lucide-vue-next'
import { api, apiError } from '../api/client'
import type { ApiResponse } from '../types'
import PageHeader from '../components/PageHeader.vue'

interface AuditItem {
  id: string
  action: string
  entity_type: string
  entity_id?: string | null
  actor_id?: string | null
  company_id?: string | null
  created_at: string
  context: Record<string, unknown>
}

const items = ref<AuditItem[]>([])
const error = ref('')
const loading = ref(false)
const search = ref('')
const visible = computed(() => {
  const value = search.value.trim().toLowerCase()
  if (!value) return items.value
  return items.value.filter(item => [item.action, item.entity_type, item.entity_id, item.actor_id, JSON.stringify(item.context)].some(field => String(field || '').toLowerCase().includes(value)))
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get<ApiResponse<AuditItem[]>>('/v1/audit', { params: { limit: 1000 } })
    items.value = response.data.data
  } catch (exception) {
    error.value = apiError(exception)
  } finally {
    loading.value = false
  }
}

function exportCsv() {
  const header = ['data', 'acao', 'entidade', 'entidade_id', 'ator_id', 'empresa_id', 'contexto']
  const quote = (value: unknown) => `"${String(value ?? '').replaceAll('"', '""')}"`
  const lines = [header.join(';'), ...visible.value.map(item => [item.created_at, item.action, item.entity_type, item.entity_id, item.actor_id, item.company_id, JSON.stringify(item.context)].map(quote).join(';'))]
  const blob = new Blob([`\uFEFF${lines.join('\n')}`], { type: 'text/csv;charset=utf-8' })
  const anchor = document.createElement('a')
  anchor.href = URL.createObjectURL(blob)
  anchor.download = `auditoria-${new Date().toISOString().slice(0, 10)}.csv`
  anchor.click()
  URL.revokeObjectURL(anchor.href)
}

onMounted(load)
</script>

<template>
  <PageHeader title="Auditoria" subtitle="Trilha append-only das operações administrativas e financeiras do tenant.">
    <button class="btn-secondary" @click="exportCsv"><Download :size="18" /> Exportar CSV</button>
    <button class="btn-primary" :disabled="loading" @click="load"><RefreshCw :size="18" :class="loading ? 'animate-spin' : ''" /> Atualizar</button>
  </PageHeader>

  <p v-if="error" class="mb-5 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{{ error }}</p>
  <div class="mb-5 flex items-center gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-soft">
    <Search :size="19" class="text-slate-400" /><input v-model="search" class="w-full bg-transparent text-sm outline-none" placeholder="Pesquisar ação, entidade, usuário ou contexto..." />
  </div>

  <div class="table-wrap">
    <table class="table">
      <thead><tr><th>Data</th><th>Ação</th><th>Entidade</th><th>Ator / Empresa</th><th>Contexto</th></tr></thead>
      <tbody>
        <tr v-for="item in visible" :key="item.id">
          <td class="whitespace-nowrap">{{ new Date(item.created_at).toLocaleString('pt-BR') }}</td>
          <td><span class="inline-flex items-center gap-2 font-semibold text-slate-900"><ShieldCheck :size="17" class="text-teal-700" />{{ item.action }}</span></td>
          <td><p class="font-medium">{{ item.entity_type }}</p><p class="max-w-xs truncate text-xs text-slate-400">{{ item.entity_id || '—' }}</p></td>
          <td><p class="max-w-xs truncate text-xs">{{ item.actor_id || 'Sistema' }}</p><p class="max-w-xs truncate text-xs text-slate-400">{{ item.company_id || 'Escopo do tenant' }}</p></td>
          <td><details class="max-w-lg"><summary class="cursor-pointer text-xs font-semibold text-teal-700">Visualizar</summary><pre class="mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded-xl bg-slate-950 p-3 text-[11px] text-emerald-300">{{ JSON.stringify(item.context || {}, null, 2) }}</pre></details></td>
        </tr>
        <tr v-if="!visible.length"><td colspan="5" class="py-12 text-center text-slate-400">Nenhum evento de auditoria encontrado.</td></tr>
      </tbody>
    </table>
  </div>
</template>
