<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { CheckCircle2, Mail, MessageCircle, Plus, Save, ServerCog, XCircle } from 'lucide-vue-next'
import { api, apiError } from '../api/client'
import type { ApiResponse, Company } from '../types'
import PageHeader from '../components/PageHeader.vue'
import ModalDialog from '../components/ModalDialog.vue'
import StatusBadge from '../components/StatusBadge.vue'

interface Integration {
  id: string
  scope: string
  company_id?: string | null
  provider: string
  is_enabled: boolean
  public_config: Record<string, unknown>
  has_secrets: boolean
  last_health_status?: string | null
  last_health_at?: string | null
  last_error?: string | null
}

type ProviderPreset = {
  provider: string
  label: string
  description: string
  publicFields: Array<{ key: string; label: string; placeholder?: string; type?: string }>
  secretFields: Array<{ key: string; label: string; placeholder?: string }>
}

const presets: ProviderPreset[] = [
  {
    provider: 'SMTP', label: 'SMTP / E-mail', description: 'Envio de boletos, recibos, notas e avisos da régua de cobrança.',
    publicFields: [
      { key: 'host', label: 'Servidor SMTP', placeholder: 'smtp.seudominio.com.br' },
      { key: 'port', label: 'Porta', placeholder: '587', type: 'number' },
      { key: 'security', label: 'Segurança', placeholder: 'STARTTLS' },
      { key: 'from_name', label: 'Nome do remetente', placeholder: 'Financeiro' },
      { key: 'from_email', label: 'E-mail remetente', placeholder: 'financeiro@dominio.com.br' }
    ],
    secretFields: [
      { key: 'username', label: 'Usuário SMTP', placeholder: 'financeiro@dominio.com.br' },
      { key: 'password', label: 'Senha SMTP', placeholder: '••••••••' }
    ]
  },
  {
    provider: 'EVOLUTION', label: 'Evolution API / WhatsApp', description: 'Mensagens transacionais, documentos e confirmação de entrega.',
    publicFields: [
      { key: 'base_url', label: 'URL da Evolution API', placeholder: 'https://evolution.exemplo.com.br' },
      { key: 'instance', label: 'Instância', placeholder: 'financeiro-tenant' },
      { key: 'webhook_url', label: 'Webhook público', placeholder: 'https://tenant.exemplo.com.br/api/v1/webhooks/evolution' }
    ],
    secretFields: [
      { key: 'api_key', label: 'API Key', placeholder: '••••••••' },
      { key: 'webhook_secret', label: 'Segredo do webhook', placeholder: '••••••••' }
    ]
  },
  {
    provider: 'NFSE', label: 'NFS-e', description: 'Credenciais e parâmetros do emissor fiscal selecionado para a empresa.',
    publicFields: [
      { key: 'provider', label: 'Provider fiscal', placeholder: 'NATIONAL / MUNICIPAL / SANDBOX' },
      { key: 'municipality_code', label: 'Código IBGE', placeholder: '2928701' },
      { key: 'environment', label: 'Ambiente', placeholder: 'HOMOLOGATION' }
    ],
    secretFields: [
      { key: 'certificate_password', label: 'Senha do certificado', placeholder: '••••••••' },
      { key: 'api_token', label: 'Token da API', placeholder: '••••••••' }
    ]
  },
  {
    provider: 'BACKUP', label: 'Backup remoto', description: 'Google Drive e Dropbox são operados pelo rclone do serviço de backup.',
    publicFields: [
      { key: 'drive_remote', label: 'Remote Google Drive', placeholder: 'gdrive:argws-financial' },
      { key: 'dropbox_remote', label: 'Remote Dropbox', placeholder: 'dropbox:argws-financial' },
      { key: 'retention_days', label: 'Retenção diária', placeholder: '14', type: 'number' }
    ],
    secretFields: []
  }
]

const integrations = ref<Integration[]>([])
const companies = ref<Company[]>([])
const modal = ref(false)
const error = ref('')
const success = ref('')
const selected = ref<ProviderPreset>(presets[0])
const form = reactive({ scope: 'TENANT', company_id: '', is_enabled: true, public_config: {} as Record<string, unknown>, secrets: {} as Record<string, string> })

const companyName = (id?: string | null) => {
  if (!id) return 'Todo o tenant'
  const item = companies.value.find(company => company.id === id)
  return item?.trade_name || item?.legal_name || id
}
const providersMissing = computed(() => presets.filter(preset => !integrations.value.some(item => item.provider === preset.provider)))

async function load() {
  error.value = ''
  try {
    const [items, companyResponse] = await Promise.all([
      api.get<ApiResponse<Integration[]>>('/v1/integrations'),
      api.get<ApiResponse<Company[]>>('/v1/companies')
    ])
    integrations.value = items.data.data
    companies.value = companyResponse.data.data
  } catch (exception) {
    error.value = apiError(exception)
  }
}

function openEditor(preset: ProviderPreset, current?: Integration) {
  selected.value = preset
  form.scope = current?.scope || 'TENANT'
  form.company_id = current?.company_id || ''
  form.is_enabled = current?.is_enabled ?? true
  form.public_config = { ...(current?.public_config || {}) }
  form.secrets = {}
  modal.value = true
  error.value = ''
  success.value = ''
}

function editIntegration(item: Integration) {
  openEditor(presets.find(preset => preset.provider === item.provider) || {
    provider: item.provider,
    label: item.provider,
    description: 'Configuração customizada do provider.',
    publicFields: [],
    secretFields: []
  }, item)
}

async function save() {
  error.value = ''
  try {
    const body = {
      scope: form.company_id ? 'COMPANY' : form.scope,
      company_id: form.company_id || null,
      is_enabled: form.is_enabled,
      public_config: form.public_config,
      secrets: Object.fromEntries(Object.entries(form.secrets).filter(([, value]) => String(value).trim() !== ''))
    }
    await api.put(`/v1/integrations/${selected.value.provider}`, body)
    success.value = `${selected.value.label} configurado com sucesso.`
    modal.value = false
    await load()
  } catch (exception) {
    error.value = apiError(exception)
  }
}

onMounted(load)
</script>

<template>
  <PageHeader title="Integrações" subtitle="SMTP, Evolution API, emissão fiscal e destinos de backup por tenant ou empresa.">
    <button class="btn-primary" @click="openEditor(providersMissing[0] || presets[0])"><Plus :size="18" /> Configurar provider</button>
  </PageHeader>

  <p v-if="error" class="mb-5 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{{ error }}</p>
  <p v-if="success" class="mb-5 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">{{ success }}</p>

  <div class="grid gap-5 xl:grid-cols-2">
    <article v-for="preset in presets" :key="preset.provider" class="card">
      <div class="flex items-start gap-4">
        <div class="rounded-2xl p-3" :class="preset.provider === 'SMTP' ? 'bg-blue-50 text-blue-700' : preset.provider === 'EVOLUTION' ? 'bg-emerald-50 text-emerald-700' : 'bg-violet-50 text-violet-700'">
          <Mail v-if="preset.provider === 'SMTP'" :size="24" />
          <MessageCircle v-else-if="preset.provider === 'EVOLUTION'" :size="24" />
          <ServerCog v-else :size="24" />
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div><h2 class="font-bold text-slate-900">{{ preset.label }}</h2><p class="text-xs font-semibold uppercase tracking-wide text-slate-400">{{ preset.provider }}</p></div>
            <button class="btn-secondary !px-3 !py-2" @click="openEditor(preset, integrations.find(item => item.provider === preset.provider))"><Save :size="16" /> Configurar</button>
          </div>
          <p class="mt-3 text-sm leading-6 text-slate-500">{{ preset.description }}</p>
        </div>
      </div>
      <div class="mt-5 space-y-3">
        <div v-for="item in integrations.filter(value => value.provider === preset.provider)" :key="item.id" class="rounded-xl border border-slate-200 p-4">
          <div class="flex items-center gap-2">
            <CheckCircle2 v-if="item.is_enabled" :size="18" class="text-emerald-600" />
            <XCircle v-else :size="18" class="text-slate-400" />
            <p class="font-semibold">{{ companyName(item.company_id) }}</p>
            <StatusBadge class="ml-auto" :status="item.is_enabled ? 'ACTIVE' : 'DISABLED'" />
          </div>
          <div class="mt-3 grid gap-2 text-xs text-slate-500 sm:grid-cols-2">
            <p>Escopo: <strong>{{ item.scope }}</strong></p>
            <p>Secrets: <strong>{{ item.has_secrets ? 'Configurados' : 'Ausentes' }}</strong></p>
            <p>Saúde: <strong>{{ item.last_health_status || 'Ainda não verificada' }}</strong></p>
            <p>Última verificação: <strong>{{ item.last_health_at ? new Date(item.last_health_at).toLocaleString('pt-BR') : '—' }}</strong></p>
          </div>
          <p v-if="item.last_error" class="mt-3 rounded-lg bg-rose-50 p-2 text-xs text-rose-700">{{ item.last_error }}</p>
          <button class="mt-3 text-xs font-semibold text-teal-700" @click="editIntegration(item)">Editar configuração</button>
        </div>
        <p v-if="!integrations.some(value => value.provider === preset.provider)" class="rounded-xl border border-dashed border-slate-200 p-4 text-center text-sm text-slate-400">Provider ainda não configurado.</p>
      </div>
    </article>
  </div>

  <ModalDialog :open="modal" :title="`Configurar ${selected.label}`" size="lg" @close="modal=false">
    <form class="space-y-5" @submit.prevent="save">
      <div class="grid gap-4 md:grid-cols-2">
        <div><label class="label">Escopo</label><select v-model="form.scope" class="select"><option value="TENANT">Todo o tenant</option><option value="COMPANY">Empresa específica</option></select></div>
        <div><label class="label">Empresa</label><select v-model="form.company_id" class="select"><option value="">Nenhuma — usar no tenant</option><option v-for="company in companies" :key="company.id" :value="company.id">{{ company.trade_name || company.legal_name }}</option></select></div>
      </div>
      <div class="grid gap-4 md:grid-cols-2">
        <div v-for="field in selected.publicFields" :key="field.key">
          <label class="label">{{ field.label }}</label>
          <input v-model="form.public_config[field.key]" :type="field.type || 'text'" :placeholder="field.placeholder" class="input" />
        </div>
      </div>
      <div v-if="selected.secretFields.length" class="rounded-2xl border border-amber-200 bg-amber-50 p-4">
        <p class="mb-3 text-sm font-semibold text-amber-900">Credenciais criptografadas</p>
        <div class="grid gap-4 md:grid-cols-2">
          <div v-for="field in selected.secretFields" :key="field.key"><label class="label">{{ field.label }}</label><input v-model="form.secrets[field.key]" type="password" :placeholder="field.placeholder" class="input" autocomplete="new-password" /></div>
        </div>
        <p class="mt-3 text-xs text-amber-800">Campos vazios preservam o segredo já salvo. O backend armazena somente o valor criptografado.</p>
      </div>
      <label class="flex items-center gap-2 text-sm font-medium text-slate-700"><input v-model="form.is_enabled" type="checkbox" /> Integração habilitada</label>
      <div class="flex justify-end gap-2"><button type="button" class="btn-secondary" @click="modal=false">Cancelar</button><button class="btn-primary"><Save :size="18" /> Salvar</button></div>
    </form>
  </ModalDialog>
</template>
