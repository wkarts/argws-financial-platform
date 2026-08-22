<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>()
</script>
<template>
  <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
    <div class="min-w-0"><h1 class="page-title">{{ title }}</h1><p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p></div>
    <div class="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end"><slot /></div>
  </div>
</template>
