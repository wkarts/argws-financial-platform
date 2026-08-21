<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { CircleDollarSign, FileClock, HandCoins, ReceiptText, Users } from 'lucide-vue-next'
import { api, apiError } from '../api/client'
import type { ApiResponse } from '../types'
import PageHeader from '../components/PageHeader.vue'
import StatCard from '../components/StatCard.vue'
interface Dashboard{open_amount:string;overdue_amount:string;received_month:string;receivables_count:number;overdue_count:number;active_contracts:number;customers:number}
const data=ref<Dashboard>({open_amount:'0',overdue_amount:'0',received_month:'0',receivables_count:0,overdue_count:0,active_contracts:0,customers:0});const error=ref('')
const money=(v:string)=>Number(v).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})
onMounted(async()=>{try{data.value=(await api.get<ApiResponse<Dashboard>>('/v1/dashboard')).data.data}catch(e){error.value=apiError(e)}})
</script>
<template><PageHeader title="Dashboard financeiro" subtitle="Visão consolidada das empresas que você pode acessar."/><p v-if="error" class="mb-5 rounded-xl bg-rose-50 p-3 text-rose-700">{{error}}</p><div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><StatCard label="Em aberto" :value="money(data.open_amount)" :icon="CircleDollarSign" tone="blue"/><StatCard label="Vencido" :value="money(data.overdue_amount)" :hint="`${data.overdue_count} títulos`" :icon="FileClock" tone="rose"/><StatCard label="Recebido no mês" :value="money(data.received_month)" :icon="HandCoins" tone="teal"/><StatCard label="Recebíveis" :value="data.receivables_count" :icon="ReceiptText" tone="amber"/></div><div class="mt-4 grid gap-4 sm:grid-cols-2"><StatCard label="Contratos ativos" :value="data.active_contracts" :icon="FileClock" tone="blue"/><StatCard label="Clientes ativos" :value="data.customers" :icon="Users" tone="teal"/></div></template>
