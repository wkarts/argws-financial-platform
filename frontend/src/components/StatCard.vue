<script setup lang="ts">
import type { Component } from 'vue'
defineProps<{ label: string; value: string | number; hint?: string; icon: Component; tone?: 'teal' | 'blue' | 'amber' | 'rose' }>()
const tones = {
  teal: 'bg-teal-50 text-teal-700', blue: 'bg-blue-50 text-blue-700',
  amber: 'bg-amber-50 text-amber-700', rose: 'bg-rose-50 text-rose-700'
}
</script>
<template>
  <div class="card flex items-start justify-between gap-4">
    <div><p class="text-sm font-medium text-slate-500">{{ label }}</p><p class="mt-2 text-2xl font-bold text-slate-900">{{ value }}</p><p v-if="hint" class="mt-1 text-xs text-slate-400">{{ hint }}</p></div>
    <div class="rounded-xl p-3" :class="tones[tone || 'teal']"><component :is="icon" :size="22" /></div>
  </div>
</template>
