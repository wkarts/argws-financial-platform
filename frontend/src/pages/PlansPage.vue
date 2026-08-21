<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Archive, Check, Edit3, Plus, RefreshCw, Save, Sparkles } from 'lucide-vue-next'
import { api } from '../api/client'
import type { ApiResponse, PlatformPlan } from '../types'
import { money } from '../utils/format'
import { useFeedback } from '../composables/useFeedback'
import PageHeader from '../components/PageHeader.vue'
import ModalDialog from '../components/ModalDialog.vue'
import InlineAlert from '../components/InlineAlert.vue'
import StatusBadge from '../components/StatusBadge.vue'
import JsonEditor from '../components/JsonEditor.vue'

const plans = ref<PlatformPlan[]>([])
const modal = ref(false)
const editing = ref<PlatformPlan | null>(null)
const includeInactive = ref(true)
const { error, success, loading, clear, fail, done } = useFeedback()
const form = reactive({
  code: '', name: '', description: '', monthly_price: '0.00', annual_price: '0.00',
  features: '{}', limits: '{}', sort_order: 0, is_public: true, is_active: true
})
const activePlans = computed(() => plans.value.filter(item => item.is_active).length)

function reset() {
  editing.value = null
  Object.assign(form, { code: '', name: '', description: '', monthly_price: '0.00', annual_price: '0.00', features: '{}', limits: '{}', sort_order: plans.value.length * 10 + 10, is_public: true, is_active: true })
}
function openCreate() { clear(); reset(); modal.value = true }
function openEdit(item: PlatformPlan) {
  clear(); editing.value = item
  Object.assign(form, {
    code: item.code, name: item.name, description: item.description || '', monthly_price: item.monthly_price,
    annual_price: item.annual_price, features: JSON.stringify(item.features, null, 2), limits: JSON.stringify(item.limits, null, 2),
    sort_order: item.sort_order, is_public: item.is_public, is_active: item.is_active
  })
  modal.value = true
}
async function load() {
  loading.value = true; error.value = ''
  try { plans.value = (await api.get<ApiResponse<PlatformPlan[]>>('/control/v1/plans', { params: { include_inactive: includeInactive.value } })).data.data }
  catch (reason) { fail(reason) } finally { loading.value = false }
}
async function save() {
  clear(); loading.value = true
  try {
    const payload = { ...form, features: JSON.parse(form.features || '{}'), limits: JSON.parse(form.limits || '{}') }
    if (editing.value) {
      const { code: _code, ...update } = payload
      await api.patch(`/control/v1/plans/${editing.value.id}`, update)
      done('Plano atualizado com sucesso.')
    } else {
      await api.post('/control/v1/plans', payload)
      done('Plano criado com sucesso.')
    }
    modal.value = false; await load()
  } catch (reason) { fail(reason) } finally { loading.value = false }
}
async function deactivate(item: PlatformPlan) {
  if (!confirm(`Desativar o plano ${item.name}? Tenants vinculados não serão removidos.`)) return
  clear(); try { await api.delete(`/control/v1/plans/${item.id}`); done('Plano desativado.'); await load() } catch (reason) { fail(reason) }
}
onMounted(load)
</script>
<template>
  <PageHeader title="Planos e capacidades" subtitle="Defina recursos, limites técnicos e valores comerciais aplicados aos tenants.">
    <label class="flex items-center gap-2 text-sm text-slate-600"><input v-model="includeInactive" type="checkbox" @change="load" /> Mostrar inativos</label>
    <button class="btn-secondary" :disabled="loading" @click="load"><RefreshCw :size="18" :class="loading && 'animate-spin'" /> Atualizar</button>
    <button class="btn-primary" @click="openCreate"><Plus :size="18" /> Novo plano</button>
  </PageHeader>
  <InlineAlert :message="error" @dismiss="error=''" />
  <InlineAlert :message="success" type="success" @dismiss="success=''" />
  <div class="mb-6 grid gap-4 sm:grid-cols-3">
    <div class="card"><p class="text-xs font-semibold uppercase tracking-wide text-slate-400">Planos cadastrados</p><p class="mt-2 text-3xl font-bold">{{ plans.length }}</p></div>
    <div class="card"><p class="text-xs font-semibold uppercase tracking-wide text-slate-400">Ativos</p><p class="mt-2 text-3xl font-bold text-emerald-700">{{ activePlans }}</p></div>
    <div class="card"><p class="text-xs font-semibold uppercase tracking-wide text-slate-400">Modelo</p><p class="mt-2 flex items-center gap-2 font-semibold"><Sparkles :size="19" class="text-amber-500" /> Feature flags + limites</p></div>
  </div>
  <div class="grid gap-5 xl:grid-cols-2">
    <article v-for="item in plans" :key="item.id" class="card relative overflow-hidden" :class="!item.is_active && 'opacity-65'">
      <div class="absolute right-0 top-0 h-24 w-24 rounded-bl-[5rem] bg-teal-50" />
      <div class="relative flex items-start justify-between gap-4">
        <div><div class="flex flex-wrap items-center gap-2"><h2 class="text-lg font-bold">{{ item.name }}</h2><StatusBadge :status="item.is_active ? 'ACTIVE' : 'INACTIVE'" /><span v-if="!item.is_public" class="badge bg-violet-100 text-violet-700">Privado</span></div><p class="mt-1 font-mono text-xs text-slate-400">{{ item.code }}</p></div>
        <button class="btn-secondary !px-3 !py-2" @click="openEdit(item)"><Edit3 :size="16" /> Editar</button>
      </div>
      <p class="relative mt-4 min-h-10 text-sm leading-relaxed text-slate-600">{{ item.description || 'Sem descrição comercial.' }}</p>
      <div class="relative mt-5 grid grid-cols-2 gap-3"><div class="rounded-xl bg-slate-50 p-3"><p class="text-xs text-slate-400">Mensal</p><p class="mt-1 font-bold">{{ money(item.monthly_price) }}</p></div><div class="rounded-xl bg-slate-50 p-3"><p class="text-xs text-slate-400">Anual</p><p class="mt-1 font-bold">{{ money(item.annual_price) }}</p></div></div>
      <div class="relative mt-5"><p class="mb-2 text-xs font-semibold uppercase text-slate-400">Recursos habilitados</p><div class="flex flex-wrap gap-2"><span v-for="(enabled,key) in item.features" :key="key" class="badge" :class="enabled ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-400'"><Check v-if="enabled" :size="12" /> {{ key }}</span></div></div>
      <div class="relative mt-4"><p class="mb-2 text-xs font-semibold uppercase text-slate-400">Limites</p><div class="grid gap-2 sm:grid-cols-2"><div v-for="(value,key) in item.limits" :key="key" class="flex justify-between rounded-lg border border-slate-100 px-3 py-2 text-xs"><span class="text-slate-500">{{ key }}</span><strong>{{ Number(value) === 0 ? 'Ilimitado' : value }}</strong></div></div></div>
      <div class="relative mt-5 flex justify-end"><button class="text-xs font-semibold text-rose-600 hover:underline" @click="deactivate(item)"><Archive :size="14" class="inline" /> Desativar</button></div>
    </article>
  </div>
  <ModalDialog :open="modal" :title="editing ? 'Editar plano' : 'Novo plano'" size="xl" @close="modal=false">
    <form class="space-y-5" @submit.prevent="save">
      <div class="grid gap-4 md:grid-cols-2"><div><label class="label">Código</label><input v-model="form.code" class="input font-mono uppercase" :disabled="Boolean(editing)" required /></div><div><label class="label">Nome</label><input v-model="form.name" class="input" required /></div><div><label class="label">Preço mensal</label><input v-model="form.monthly_price" class="input" type="number" min="0" step="0.01" /></div><div><label class="label">Preço anual</label><input v-model="form.annual_price" class="input" type="number" min="0" step="0.01" /></div><div class="md:col-span-2"><label class="label">Descrição</label><textarea v-model="form.description" class="input" rows="3" /></div></div>
      <div class="grid gap-4 lg:grid-cols-2"><JsonEditor v-model="form.features" label="Feature flags" :rows="12" hint="Objeto com recursos booleanos, por exemplo pix_automatic e custom_domain." /><JsonEditor v-model="form.limits" label="Limites" :rows="12" hint="Valor 0 representa ilimitado." /></div>
      <div class="grid gap-4 md:grid-cols-3"><div><label class="label">Ordem</label><input v-model.number="form.sort_order" class="input" type="number" /></div><label class="flex items-center gap-2 pt-8 text-sm"><input v-model="form.is_public" type="checkbox" /> Visível comercialmente</label><label class="flex items-center gap-2 pt-8 text-sm"><input v-model="form.is_active" type="checkbox" /> Plano ativo</label></div>
      <div class="flex justify-end gap-2"><button type="button" class="btn-secondary" @click="modal=false">Cancelar</button><button class="btn-primary" :disabled="loading"><Save :size="18" /> Salvar plano</button></div>
    </form>
  </ModalDialog>
</template>
