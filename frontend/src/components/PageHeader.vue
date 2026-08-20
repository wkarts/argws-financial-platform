<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>()
</script>
<template>
  <div class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
    <div><h1 class="page-title">{{ title }}</h1><p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p></div>
    <div class="flex flex-wrap items-center gap-2"><slot /></div>
  </div>
</template>
