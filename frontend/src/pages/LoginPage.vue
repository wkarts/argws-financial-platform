<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { BadgeDollarSign, Eye, EyeOff, LockKeyhole, Mail } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { apiError } from '../api/client'

const auth = useAuthStore()
const router = useRouter()
const email = ref('')
const password = ref('')
const showPassword = ref(false)
const error = ref('')
const title = computed(() => auth.isControlPlane ? 'Control Plane' : 'Acesso Financeiro')

async function submit() {
  error.value = ''
  try { await auth.login(email.value, password.value); await router.push('/') }
  catch (e) { error.value = apiError(e) }
}
</script>
<template>
  <div class="relative grid min-h-screen place-items-center overflow-hidden bg-slate-950 p-4">
    <div class="absolute inset-0 opacity-30" style="background: radial-gradient(circle at 15% 20%, #14b8a6 0, transparent 25%), radial-gradient(circle at 85% 80%, #2563eb 0, transparent 28%)" />
    <div class="relative grid w-full max-w-5xl overflow-hidden rounded-3xl border border-white/10 bg-white shadow-2xl lg:grid-cols-[1.1fr_.9fr]">
      <section class="hidden bg-gradient-to-br from-teal-700 to-slate-950 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div class="flex items-center gap-3"><div class="grid h-12 w-12 place-items-center rounded-2xl bg-white/10"><BadgeDollarSign :size="28" /></div><div><p class="font-bold">ARGWS Financial Platform</p><p class="text-sm text-teal-100">SaaS financeiro multitenant</p></div></div>
        <div><h1 class="max-w-lg text-4xl font-bold leading-tight">Cobranças, recorrência e recebíveis em uma única operação segura.</h1><p class="mt-5 max-w-lg text-base leading-relaxed text-slate-200">Isolamento por tenant, múltiplas empresas, boletos, PIX, CNAB, SMTP, WhatsApp e conciliação.</p></div>
        <p class="text-xs text-slate-400">Python 3.13 · FastAPI · PostgreSQL · Vue 3 PWA</p>
      </section>
      <section class="p-7 sm:p-10 lg:p-12">
        <div class="mb-8 lg:hidden"><div class="mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-teal-700 text-white"><BadgeDollarSign :size="28" /></div></div>
        <p class="text-sm font-semibold uppercase tracking-wider text-teal-700">{{ title }}</p><h2 class="mt-2 text-3xl font-bold text-slate-900">Entre na sua conta</h2><p class="mt-2 text-sm text-slate-500">Use as credenciais fornecidas pelo administrador.</p>
        <form class="mt-8 space-y-5" @submit.prevent="submit">
          <div><label class="label">E-mail</label><div class="relative"><Mail class="absolute left-3.5 top-3 text-slate-400" :size="19" /><input v-model="email" type="email" required autocomplete="username" class="input pl-11" placeholder="seu@email.com" /></div></div>
          <div><label class="label">Senha</label><div class="relative"><LockKeyhole class="absolute left-3.5 top-3 text-slate-400" :size="19" /><input v-model="password" :type="showPassword ? 'text' : 'password'" required autocomplete="current-password" class="input pl-11 pr-11" placeholder="••••••••••••" /><button type="button" class="absolute right-3 top-2.5 rounded-lg p-1 text-slate-400 hover:text-slate-700" @click="showPassword = !showPassword"><EyeOff v-if="showPassword" :size="19" /><Eye v-else :size="19" /></button></div></div>
          <p v-if="error" class="rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{{ error }}</p>
          <button class="btn-primary w-full" :disabled="auth.loading">{{ auth.loading ? 'Autenticando…' : 'Entrar' }}</button>
        </form>
      </section>
    </div>
  </div>
</template>
