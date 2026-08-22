<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, BadgeDollarSign, ShieldCheck, WalletCards } from 'lucide-vue-next'
import { api, apiError } from '../api/client'
import type { ApiResponse } from '../types'

interface PublicSite {
  name: string
  hostname: string
  demo_mode: boolean
  landing: {
    mode: 'DISABLED' | 'PLATFORM' | 'EXTERNAL'
    url: string
    title: string
    subtitle: string
    cta_label: string
    cta_url: string
  }
}

const router = useRouter()
const site = ref<PublicSite | null>(null)
const error = ref('')

function safeLocalTarget(value: string): string {
  const target = String(value || '').trim()
  if (!target || !target.startsWith('/') || target.startsWith('//')) return '/login'
  return target
}

async function openCta() {
  const target = safeLocalTarget(site.value?.landing.cta_url || '/login')
  await router.push(target)
}

onMounted(async () => {
  try {
    const response = await api.get<ApiResponse<PublicSite>>('/v1/public/site')
    site.value = response.data.data
    if (site.value.landing.mode === 'DISABLED') {
      await router.replace('/login')
      return
    }
    if (site.value.landing.mode === 'EXTERNAL') {
      if (site.value.landing.url) window.location.replace(site.value.landing.url)
      else await router.replace('/login')
    }
  } catch (exception) {
    error.value = apiError(exception)
  }
})
</script>

<template>
  <main class="min-h-screen bg-slate-950 text-white">
    <div class="pointer-events-none fixed inset-0 opacity-80" style="background:radial-gradient(circle at 12% 18%,rgba(13,148,136,.35),transparent 34%),radial-gradient(circle at 82% 78%,rgba(37,99,235,.22),transparent 34%)" />
    <div class="relative mx-auto flex min-h-screen w-full max-w-7xl flex-col px-5 py-8 sm:px-8 lg:px-12">
      <header class="flex items-center justify-between gap-4">
        <div class="flex min-w-0 items-center gap-3">
          <div class="grid h-11 w-11 shrink-0 place-items-center rounded-2xl border border-white/10 bg-white/10 text-teal-200"><BadgeDollarSign :size="25"/></div>
          <div class="min-w-0"><p class="truncate font-semibold">{{ site?.name || 'ARGWS Financial Platform' }}</p><p class="truncate text-xs text-slate-400">Gestão financeira integrada</p></div>
        </div>
        <button class="rounded-xl border border-white/15 bg-white/10 px-4 py-2 text-sm font-semibold transition hover:bg-white/15" @click="router.push('/login')">Entrar</button>
      </header>

      <section v-if="error" class="my-auto rounded-2xl border border-rose-300/20 bg-rose-400/10 p-5 text-rose-100">
        <p class="font-semibold">Não foi possível carregar esta página.</p><p class="mt-2 text-sm opacity-80">{{ error }}</p><button class="mt-4 rounded-xl bg-white px-4 py-2 text-sm font-semibold text-slate-900" @click="router.push('/login')">Acessar área financeira</button>
      </section>

      <section v-else-if="site" class="my-auto grid items-center gap-12 py-16 lg:grid-cols-[1.1fr_.9fr] lg:py-24">
        <div>
          <div v-if="site.demo_mode" class="mb-6 inline-flex items-center gap-2 rounded-full border border-amber-300/20 bg-amber-300/10 px-3.5 py-2 text-sm font-semibold text-amber-100">Ambiente de demonstração</div>
          <h1 class="max-w-4xl text-4xl font-semibold leading-tight tracking-[-0.04em] sm:text-5xl lg:text-6xl">{{ site.landing.title }}</h1>
          <p class="mt-6 max-w-2xl text-base leading-7 text-slate-300 sm:text-lg">{{ site.landing.subtitle }}</p>
          <div class="mt-8 flex flex-wrap gap-3">
            <button class="inline-flex min-h-12 items-center gap-2 rounded-xl bg-teal-500 px-5 py-3 font-semibold text-slate-950 transition hover:bg-teal-400" @click="openCta">{{ site.landing.cta_label }}<ArrowRight :size="18"/></button>
            <button class="min-h-12 rounded-xl border border-white/15 px-5 py-3 font-semibold text-white transition hover:bg-white/10" @click="router.push('/login')">Já tenho acesso</button>
          </div>
        </div>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
          <article class="rounded-2xl border border-white/10 bg-white/[0.06] p-5 backdrop-blur"><WalletCards :size="23" class="text-teal-200"/><h2 class="mt-4 font-semibold">Cobranças e recebíveis</h2><p class="mt-2 text-sm leading-6 text-slate-400">Organização de contratos, cobranças, pagamentos e conciliação.</p></article>
          <article class="rounded-2xl border border-white/10 bg-white/[0.06] p-5 backdrop-blur"><ShieldCheck :size="23" class="text-teal-200"/><h2 class="mt-4 font-semibold">Acesso protegido</h2><p class="mt-2 text-sm leading-6 text-slate-400">Área financeira restrita a usuários autorizados pela empresa.</p></article>
        </div>
      </section>

      <footer class="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-5 text-xs text-slate-500"><span>{{ site?.hostname }}</span><span>ARGWS Financial Platform</span></footer>
    </div>
  </main>
</template>
