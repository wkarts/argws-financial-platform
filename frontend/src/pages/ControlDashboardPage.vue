<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Activity, Building2, CircleCheck, Globe2, TriangleAlert } from 'lucide-vue-next'
import { api, apiError } from '../api/client'
import type { ApiResponse } from '../types'
import PageHeader from '../components/PageHeader.vue'
import StatCard from '../components/StatCard.vue'

interface Dashboard { tenants: number; active: number; provisioning: number; failed: number; domains: number }
const data = ref<Dashboard>({ tenants: 0, active: 0, provisioning: 0, failed: 0, domains: 0 })
const error = ref('')
onMounted(async () => { try { data.value = (await api.get<ApiResponse<Dashboard>>('/control/v1/dashboard')).data.data } catch (e) { error.value = apiError(e) } })
</script>
<template>
  <PageHeader title="Control Plane" subtitle="Governança central da plataforma, tenants e provisionamento." />
  <p v-if="error" class="mb-5 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{{ error }}</p>
  <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
    <StatCard label="Tenants" :value="data.tenants" :icon="Building2" tone="blue" />
    <StatCard label="Ativos" :value="data.active" :icon="CircleCheck" tone="teal" />
    <StatCard label="Provisionando" :value="data.provisioning" :icon="Activity" tone="amber" />
    <StatCard label="Com falha" :value="data.failed" :icon="TriangleAlert" tone="rose" />
    <StatCard label="Domínios" :value="data.domains" :icon="Globe2" tone="blue" />
  </div>
  <div class="mt-6 grid gap-6 lg:grid-cols-2">
    <section class="card"><h2 class="font-semibold">Responsabilidades do Control Plane</h2><div class="mt-4 grid gap-3 text-sm text-slate-600"><p>Provisionamento de banco, storage, domínio e administrador.</p><p>Planos, limites, feature flags, suspensão e reativação.</p><p>Auditoria global, saúde operacional e políticas de backup.</p></div></section>
    <section class="card"><h2 class="font-semibold">Isolamento ativo</h2><p class="mt-3 text-sm leading-relaxed text-slate-600">Cada tenant opera em banco PostgreSQL e namespace S3 próprios. A resolução ocorre exclusivamente pelo hostname registrado, sem fallback entre organizações.</p></section>
  </div>
</template>
