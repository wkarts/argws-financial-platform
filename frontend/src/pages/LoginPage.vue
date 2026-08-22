<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  BadgeDollarSign,
  CheckCircle2,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldCheck,
  Sparkles,
  WalletCards,
} from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { apiError } from '../api/client'

const auth = useAuthStore()
const router = useRouter()
const email = ref('')
const password = ref('')
const showPassword = ref(false)
const error = ref('')

const accessLabel = computed(() => (auth.isControlPlane ? 'Área administrativa' : 'Área financeira'))
const heading = computed(() => (auth.isControlPlane ? 'Acesse a administração' : 'Bem-vindo de volta'))
const description = computed(() =>
  auth.isControlPlane
    ? 'Entre para administrar empresas e acompanhar a operação financeira.'
    : 'Acesse seus dados financeiros com segurança e praticidade.',
)

async function submit() {
  error.value = ''
  try {
    await auth.login(email.value, password.value)
    await router.push('/')
  } catch (e) {
    error.value = apiError(e)
  }
}
</script>

<template>
  <main class="relative min-h-screen overflow-hidden bg-slate-950">
    <div
      class="pointer-events-none absolute inset-0 opacity-70"
      style="background:
        radial-gradient(circle at 10% 15%, rgba(13, 148, 136, .30), transparent 32%),
        radial-gradient(circle at 88% 82%, rgba(37, 99, 235, .20), transparent 34%);"
    />

    <div class="relative mx-auto grid min-h-screen w-full max-w-[1500px] lg:grid-cols-[1.08fr_.92fr]">
      <section class="relative hidden overflow-hidden border-r border-white/10 px-14 py-12 text-white lg:flex lg:flex-col xl:px-20 xl:py-16">
        <div
          class="pointer-events-none absolute -right-48 -top-48 h-[560px] w-[560px] rounded-full border border-white/10"
        />
        <div
          class="pointer-events-none absolute -right-28 -top-28 h-[400px] w-[400px] rounded-full border border-white/10"
        />

        <div class="relative flex items-center gap-3">
          <div class="grid h-12 w-12 place-items-center rounded-2xl border border-white/10 bg-white/10 shadow-lg shadow-black/10">
            <BadgeDollarSign :size="27" />
          </div>
          <div>
            <p class="text-base font-semibold tracking-tight">ARGWS Financeiro</p>
            <p class="mt-0.5 text-sm text-slate-300">Gestão financeira integrada</p>
          </div>
        </div>

        <div class="relative my-auto max-w-2xl py-14">
          <div class="mb-6 inline-flex items-center gap-2 rounded-full border border-teal-300/20 bg-teal-300/10 px-3.5 py-2 text-sm font-medium text-teal-100">
            <Sparkles :size="16" />
            Clareza para decidir. Controle para crescer.
          </div>

          <h1 class="max-w-2xl text-5xl font-semibold leading-[1.08] tracking-[-0.035em] xl:text-6xl">
            Seu financeiro sob controle, do recebimento à conciliação.
          </h1>

          <p class="mt-7 max-w-xl text-lg leading-8 text-slate-300">
            Centralize cobranças, contratos, recorrências e recebimentos em uma experiência segura,
            organizada e preparada para a rotina da sua empresa.
          </p>

          <div class="mt-10 grid max-w-2xl gap-3 sm:grid-cols-3">
            <div class="rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-sm">
              <WalletCards :size="20" class="text-teal-200" />
              <p class="mt-3 text-sm font-semibold">Cobranças e recorrências</p>
              <p class="mt-1 text-xs leading-5 text-slate-400">Organização do ciclo financeiro.</p>
            </div>
            <div class="rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-sm">
              <BadgeDollarSign :size="20" class="text-teal-200" />
              <p class="mt-3 text-sm font-semibold">Recebimentos e Pix</p>
              <p class="mt-1 text-xs leading-5 text-slate-400">Visibilidade sobre entradas e valores.</p>
            </div>
            <div class="rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-sm">
              <CheckCircle2 :size="20" class="text-teal-200" />
              <p class="mt-3 text-sm font-semibold">Conciliação e acompanhamento</p>
              <p class="mt-1 text-xs leading-5 text-slate-400">Informação confiável para agir.</p>
            </div>
          </div>
        </div>

        <div class="relative flex items-center gap-2 text-xs text-slate-400">
          <ShieldCheck :size="15" />
          Ambiente protegido · acesso restrito a usuários autorizados
        </div>
      </section>

      <section class="flex min-h-screen items-center justify-center bg-slate-50/95 px-5 py-10 sm:px-8 lg:bg-white">
        <div class="w-full max-w-md">
          <div class="mb-10 lg:hidden">
            <div class="flex items-center gap-3">
              <div class="grid h-12 w-12 place-items-center rounded-2xl bg-teal-700 text-white shadow-lg shadow-teal-900/10">
                <BadgeDollarSign :size="27" />
              </div>
              <div>
                <p class="font-semibold text-slate-950">ARGWS Financeiro</p>
                <p class="text-sm text-slate-500">Gestão financeira integrada</p>
              </div>
            </div>
          </div>

          <div class="mb-9">
            <div class="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.14em] text-teal-700">
              <ShieldCheck :size="17" />
              {{ accessLabel }}
            </div>
            <h2 class="text-4xl font-semibold tracking-[-0.035em] text-slate-950">
              {{ heading }}
            </h2>
            <p class="mt-3 max-w-sm text-sm leading-6 text-slate-500">
              {{ description }}
            </p>
          </div>

          <form class="space-y-5" @submit.prevent="submit">
            <div>
              <label for="financial-login-email" class="label">E-mail</label>
              <div class="relative mt-1.5">
                <Mail class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" :size="19" />
                <input
                  id="financial-login-email"
                  v-model.trim="email"
                  type="email"
                  required
                  autocomplete="username"
                  class="input h-12 pl-11"
                  placeholder="seu@email.com"
                />
              </div>
            </div>

            <div>
              <div class="flex items-center justify-between">
                <label for="financial-login-password" class="label">Senha</label>
                <span class="text-xs text-slate-400">Acesso protegido</span>
              </div>
              <div class="relative mt-1.5">
                <LockKeyhole class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" :size="19" />
                <input
                  id="financial-login-password"
                  v-model="password"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  autocomplete="current-password"
                  class="input h-12 pl-11 pr-12"
                  placeholder="Digite sua senha"
                />
                <button
                  type="button"
                  class="absolute right-2.5 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-600/30"
                  :aria-label="showPassword ? 'Ocultar senha' : 'Mostrar senha'"
                  :title="showPassword ? 'Ocultar senha' : 'Mostrar senha'"
                  @click="showPassword = !showPassword"
                >
                  <EyeOff v-if="showPassword" :size="19" />
                  <Eye v-else :size="19" />
                </button>
              </div>
            </div>

            <p
              v-if="error"
              role="alert"
              class="rounded-xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm leading-5 text-rose-700"
            >
              {{ error }}
            </p>

            <button class="btn-primary h-12 w-full text-sm font-semibold" :disabled="auth.loading">
              {{ auth.loading ? 'Validando acesso…' : 'Entrar' }}
            </button>
          </form>

          <div class="mt-8 flex items-center justify-center gap-2 text-xs text-slate-400 lg:hidden">
            <ShieldCheck :size="14" />
            Ambiente protegido
          </div>
        </div>
      </section>
    </div>
  </main>
</template>
