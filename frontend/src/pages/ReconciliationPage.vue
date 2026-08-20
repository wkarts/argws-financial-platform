<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CheckCircle2, RefreshCw, WandSparkles } from 'lucide-vue-next'
import { api, apiError } from '../api/client'
import type { ApiResponse, Paginated, Payment, Receivable } from '../types'
import PageHeader from '../components/PageHeader.vue'
import StatusBadge from '../components/StatusBadge.vue'

interface Reconciliation {
  id: string
  receivable_id?: string | null
  payment_id?: string | null
  bank_transaction_id?: string | null
  status: string
  score: string
  criteria: Record<string, unknown>
  reconciled_at?: string | null
  created_at: string
}

const items = ref<Reconciliation[]>([])
const receivables = ref<Receivable[]>([])
const payments = ref<Payment[]>([])
const error = ref('')
const message = ref('')
const loading = ref(false)
const money = (value: string | number) => Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
const receivableById = computed(() => new Map(receivables.value.map(item => [item.id, item])))
const paymentById = computed(() => new Map(payments.value.map(item => [item.id, item])))

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [r, rec, pay] = await Promise.all([
      api.get<ApiResponse<Reconciliation[]>>('/v1/reconciliations'),
      api.get<Paginated<Receivable>>('/v1/receivables', { params: { per_page: 100 } }),
      api.get<ApiResponse<Payment[]>>('/v1/payments')
    ])
    items.value = r.data.data
    receivables.value = rec.data.data
    payments.value = pay.data.data
  } catch (exception) {
    error.value = apiError(exception)
  } finally {
    loading.value = false
  }
}

async function autoMatch() {
  error.value = ''
  try {
    const response = await api.post<ApiResponse<{ matched: number }>>('/v1/reconciliations/auto-match')
    message.value = `${response.data.data.matched} pagamento(s) conciliado(s) de forma idempotente.`
    await load()
  } catch (exception) {
    error.value = apiError(exception)
  }
}

onMounted(load)
</script>

<template>
  <PageHeader title="Conciliação" subtitle="Correspondência auditável entre recebíveis, pagamentos e transações bancárias.">
    <button class="btn-secondary" :disabled="loading" @click="load"><RefreshCw :size="18" :class="loading ? 'animate-spin' : ''" /> Atualizar</button>
    <button class="btn-primary" @click="autoMatch"><WandSparkles :size="18" /> Conciliar automaticamente</button>
  </PageHeader>
  <p v-if="error" class="mb-5 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{{ error }}</p>
  <p v-if="message" class="mb-5 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">{{ message }}</p>
  <div class="table-wrap">
    <table class="table">
      <thead><tr><th>Recebível</th><th>Pagamento</th><th>Transação bancária</th><th>Critérios</th><th>Confiança</th><th>Status</th></tr></thead>
      <tbody>
        <tr v-for="item in items" :key="item.id">
          <td><p class="font-semibold">{{ receivableById.get(item.receivable_id || '')?.document_number || item.receivable_id || '—' }}</p><p class="text-xs text-slate-400">{{ receivableById.get(item.receivable_id || '')?.description || '' }}</p></td>
          <td><p class="font-semibold">{{ paymentById.get(item.payment_id || '') ? money(paymentById.get(item.payment_id || '')!.amount) : '—' }}</p><p class="text-xs text-slate-400">{{ paymentById.get(item.payment_id || '')?.provider || '' }}</p></td>
          <td class="max-w-xs truncate text-xs">{{ item.bank_transaction_id || '—' }}</td>
          <td><details><summary class="cursor-pointer text-xs font-semibold text-teal-700">Detalhes</summary><pre class="mt-2 max-w-sm whitespace-pre-wrap rounded-lg bg-slate-950 p-2 text-[10px] text-emerald-300">{{ JSON.stringify(item.criteria, null, 2) }}</pre></details></td>
          <td><span class="inline-flex items-center gap-1 font-semibold"><CheckCircle2 :size="16" class="text-emerald-600" />{{ Number(item.score).toFixed(0) }}%</span></td>
          <td><StatusBadge :status="item.status" /></td>
        </tr>
        <tr v-if="!items.length"><td colspan="6" class="py-12 text-center text-slate-400">Nenhuma conciliação registrada.</td></tr>
      </tbody>
    </table>
  </div>
</template>
