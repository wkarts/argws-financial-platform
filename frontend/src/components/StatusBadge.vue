<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ status: string }>()
const classes = computed(() => {
  const value = props.status.toUpperCase()
  if (['ACTIVE','PAID','SUCCEEDED','REGISTERED','SENT','DELIVERED','READ','PROCESSED'].includes(value)) return 'bg-emerald-100 text-emerald-700'
  if (['PENDING','PROVISIONING','RUNNING','VERIFYING','WAITING_SSL','OPEN','PARTIALLY_PAID'].includes(value)) return 'bg-amber-100 text-amber-700'
  if (['FAILED','ERROR','OVERDUE','BLOCKED','PROVISIONING_FAILED'].includes(value)) return 'bg-rose-100 text-rose-700'
  if (['SUSPENDED','CANCELLED','ARCHIVED'].includes(value)) return 'bg-slate-200 text-slate-700'
  return 'bg-blue-100 text-blue-700'
})
</script>
<template><span class="badge" :class="classes">{{ status }}</span></template>
