<script setup lang="ts">
import { computed } from 'vue'
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-vue-next'
const props = withDefaults(defineProps<{ message?: string; type?: 'error'|'success'|'info'; tone?: 'error'|'success'|'info'; dismissible?: boolean }>(), { type: 'error', dismissible: true })
const emit = defineEmits<{ dismiss: [] }>()
const resolved = computed(() => props.tone || props.type)
</script>
<template>
  <div v-if="message" class="flex items-start gap-3 rounded-xl border p-3 text-sm"
       :class="resolved === 'error' ? 'border-rose-200 bg-rose-50 text-rose-800' : resolved === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-sky-200 bg-sky-50 text-sky-800'">
    <AlertCircle v-if="resolved === 'error'" :size="18" class="mt-0.5 shrink-0" />
    <CheckCircle2 v-else-if="resolved === 'success'" :size="18" class="mt-0.5 shrink-0" />
    <Info v-else :size="18" class="mt-0.5 shrink-0" />
    <span class="flex-1 whitespace-pre-wrap">{{ message }}</span>
    <button v-if="dismissible" type="button" class="rounded p-0.5 opacity-60 hover:opacity-100" @click="emit('dismiss')"><X :size="16" /></button>
  </div>
</template>
