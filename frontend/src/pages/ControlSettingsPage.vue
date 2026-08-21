<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Cloud, KeyRound, Plus, Save, Settings2 } from 'lucide-vue-next'
import { api, apiError } from '../api/client'
import type { ApiResponse, PlatformSetting } from '../types'
import PageHeader from '../components/PageHeader.vue'
import ModalDialog from '../components/ModalDialog.vue'
import InlineAlert from '../components/InlineAlert.vue'
import JsonEditor from '../components/JsonEditor.vue'
import StatusBadge from '../components/StatusBadge.vue'

interface PlatformIntegration {
  id: string
  provider: string
  is_enabled: boolean
  public_config: Record<string, unknown>
  has_secrets: boolean
  health_status?: string
  health_checked_at?: string
  last_error?: string
}

const settings = ref<PlatformSetting[]>([])
const integrations = ref<PlatformIntegration[]>([])
const error = ref('')
const success = ref('')
const settingModal = ref(false)
const integrationModal = ref(false)
const settingForm = reactive({ key: '', category: 'GENERAL', description: '', is_secret: false, value: {} as Record<string, unknown> })
const integrationForm = reactive({ provider: 'SMTP', is_enabled: true, public_config: {} as Record<string, unknown>, secrets: {} as Record<string, unknown> })
const categories = computed(() => [...new Set(settings.value.map(item => item.category))].sort())

async function load() {
  error.value = ''
  try {
    const [settingResponse, integrationResponse] = await Promise.all([
      api.get<ApiResponse<PlatformSetting[]>>('/control/v1/settings'),
      api.get<ApiResponse<PlatformIntegration[]>>('/control/v1/platform-integrations')
    ])
    settings.value = settingResponse.data.data
    integrations.value = integrationResponse.data.data
  } catch (exception) { error.value = apiError(exception) }
}

function openSetting(item?: PlatformSetting) {
  Object.assign(settingForm, {
    key: item?.key || '', category: item?.category || 'GENERAL', description: item?.description || '',
    is_secret: item?.is_secret || false, value: { ...(item?.value || {}) }
  })
  settingModal.value = true
}

async function saveSetting() {
  error.value = ''
  try {
    await api.put(`/control/v1/settings/${settingForm.key}`, {
      category: settingForm.category, description: settingForm.description || null,
      is_secret: settingForm.is_secret, value: settingForm.value
    })
    settingModal.value = false; success.value = 'Configuração salva.'; await load()
  } catch (exception) { error.value = apiError(exception) }
}

function openIntegration(item?: PlatformIntegration) {
  Object.assign(integrationForm, {
    provider: item?.provider || 'SMTP', is_enabled: item?.is_enabled ?? true,
    public_config: { ...(item?.public_config || {}) }, secrets: {}
  })
  integrationModal.value = true
}

async function saveIntegration() {
  error.value = ''
  try {
    await api.put(`/control/v1/platform-integrations/${integrationForm.provider}`, {
      is_enabled: integrationForm.is_enabled, public_config: integrationForm.public_config,
      secrets: integrationForm.secrets
    })
    integrationModal.value = false; success.value = 'Integração global atualizada.'; await load()
  } catch (exception) { error.value = apiError(exception) }
}

onMounted(load)
</script>

<template>
  <PageHeader title="Configurações da plataforma" subtitle="Parâmetros globais, defaults e integrações compartilhadas pelo Control Plane.">
    <button class="btn-secondary" @click="openIntegration()"><Cloud :size="18" /> Nova integração</button>
    <button class="btn-primary" @click="openSetting()"><Plus :size="18" /> Nova configuração</button>
  </PageHeader>
  <InlineAlert v-if="error" tone="error" :message="error" class="mb-5" />
  <InlineAlert v-if="success" tone="success" :message="success" class="mb-5" />

  <section class="grid gap-6 xl:grid-cols-[1.35fr_.65fr]">
    <div class="space-y-5">
      <div v-for="category in categories" :key="category" class="card !p-0 overflow-hidden">
        <div class="flex items-center gap-3 border-b border-slate-200 px-5 py-4"><Settings2 :size="20" class="text-teal-700" /><h2 class="font-semibold">{{ category }}</h2></div>
        <div class="divide-y divide-slate-100">
          <button v-for="item in settings.filter(value => value.category === category)" :key="item.id" class="flex w-full items-start gap-4 px-5 py-4 text-left hover:bg-slate-50" @click="openSetting(item)">
            <div class="mt-0.5 rounded-xl bg-slate-100 p-2 text-slate-600"><KeyRound :size="17" /></div>
            <div class="min-w-0 flex-1"><p class="font-semibold text-slate-900">{{ item.key }}</p><p class="mt-1 text-sm text-slate-500">{{ item.description || 'Sem descrição.' }}</p><pre v-if="!item.is_secret" class="mt-2 max-h-24 overflow-auto whitespace-pre-wrap text-xs text-slate-400">{{ JSON.stringify(item.value, null, 2) }}</pre></div>
            <StatusBadge :status="item.is_secret ? 'SECRET' : 'PUBLIC'" />
          </button>
        </div>
      </div>
      <div v-if="!settings.length" class="card text-center text-sm text-slate-400">Nenhuma configuração persistida.</div>
    </div>

    <div class="space-y-4">
      <h2 class="text-lg font-semibold">Integrações globais</h2>
      <article v-for="item in integrations" :key="item.id" class="card">
        <div class="flex items-center justify-between gap-3"><div><p class="font-semibold">{{ item.provider }}</p><p class="text-xs text-slate-400">Secrets: {{ item.has_secrets ? 'configurados' : 'ausentes' }}</p></div><StatusBadge :status="item.is_enabled ? item.health_status || 'ACTIVE' : 'DISABLED'" /></div>
        <pre class="mt-4 max-h-40 overflow-auto rounded-xl bg-slate-950 p-3 text-[11px] text-emerald-300">{{ JSON.stringify(item.public_config, null, 2) }}</pre>
        <p v-if="item.last_error" class="mt-3 text-xs text-rose-600">{{ item.last_error }}</p>
        <button class="btn-secondary mt-4 w-full" @click="openIntegration(item)"><Save :size="16" /> Editar</button>
      </article>
      <div v-if="!integrations.length" class="card text-center text-sm text-slate-400">Nenhuma integração global configurada.</div>
    </div>
  </section>

  <ModalDialog :open="settingModal" title="Configuração da plataforma" size="lg" @close="settingModal=false">
    <form class="space-y-4" @submit.prevent="saveSetting">
      <div class="grid gap-4 md:grid-cols-2"><div><label class="label">Chave</label><input v-model="settingForm.key" class="input" required /></div><div><label class="label">Categoria</label><input v-model="settingForm.category" class="input" required /></div></div>
      <div><label class="label">Descrição</label><textarea v-model="settingForm.description" class="input min-h-20" /></div>
      <JsonEditor v-model="settingForm.value" label="Valor JSON" />
      <label class="flex items-center gap-2 text-sm"><input v-model="settingForm.is_secret" type="checkbox" /> Tratar valor como segredo criptografado</label>
      <div class="flex justify-end gap-2"><button type="button" class="btn-secondary" @click="settingModal=false">Cancelar</button><button class="btn-primary"><Save :size="18" /> Salvar</button></div>
    </form>
  </ModalDialog>

  <ModalDialog :open="integrationModal" title="Integração global" size="lg" @close="integrationModal=false">
    <form class="space-y-4" @submit.prevent="saveIntegration">
      <div><label class="label">Provider</label><input v-model="integrationForm.provider" class="input" required /></div>
      <JsonEditor v-model="integrationForm.public_config" label="Configuração pública" />
      <JsonEditor v-model="integrationForm.secrets" label="Secrets — campos vazios preservam os atuais" />
      <label class="flex items-center gap-2 text-sm"><input v-model="integrationForm.is_enabled" type="checkbox" /> Provider habilitado</label>
      <div class="flex justify-end gap-2"><button type="button" class="btn-secondary" @click="integrationModal=false">Cancelar</button><button class="btn-primary"><Save :size="18" /> Salvar</button></div>
    </form>
  </ModalDialog>
</template>
