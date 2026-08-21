<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  BellRing,
  Clock3,
  Mail,
  MessageCircle,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  Save,
  Send,
  Trash2,
} from 'lucide-vue-next'
import { api, apiError } from '../api/client'
import type { ApiResponse, Company } from '../types'
import PageHeader from '../components/PageHeader.vue'
import ModalDialog from '../components/ModalDialog.vue'
import StatusBadge from '../components/StatusBadge.vue'

interface Notification {
  id: string
  company_id?: string | null
  customer_id?: string | null
  receivable_id?: string | null
  channel: string
  provider: string
  destination: string
  subject?: string | null
  body: string
  status: string
  external_id?: string | null
  attempts: number
  scheduled_at: string
  sent_at?: string | null
  delivered_at?: string | null
  read_at?: string | null
  created_at: string
  last_error?: string | null
}

interface RuleEvent {
  offset_days: number
  channels: string[]
  template: string
}

interface NotificationRule {
  id: string
  name: string
  events: RuleEvent[]
  is_default: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

interface NotificationTemplate {
  id: string
  code: string
  channel: string
  subject?: string | null
  body: string
  is_active: boolean
  created_at: string
  updated_at: string
}

type Tab = 'history' | 'rules' | 'templates'

const tabs: Array<{ id: Tab; label: string; icon: typeof BellRing }> = [
  { id: 'history', label: 'Histórico', icon: BellRing },
  { id: 'rules', label: 'Régua de cobrança', icon: Clock3 },
  { id: 'templates', label: 'Templates', icon: Mail },
]

const tab = ref<Tab>('history')
const notifications = ref<Notification[]>([])
const rules = ref<NotificationRule[]>([])
const templates = ref<NotificationTemplate[]>([])
const companies = ref<Company[]>([])
const loading = ref(false)
const saving = ref(false)
const testModal = ref(false)
const ruleModal = ref(false)
const templateModal = ref(false)
const error = ref('')
const result = ref('')
const filter = ref('')

const testForm = reactive({
  channel: 'EMAIL',
  company_id: '',
  destination: '',
  subject: 'Teste de comunicação',
  body: 'Mensagem de teste da Plataforma Financeira ARGWS.',
})
const ruleForm = reactive<{
  id: string
  name: string
  events: RuleEvent[]
  is_default: boolean
  is_active: boolean
}>({ id: '', name: '', events: [], is_default: false, is_active: true })
const templateForm = reactive({
  id: '',
  code: '',
  channel: 'EMAIL',
  subject: '',
  body: '',
  is_active: true,
})

const visibleNotifications = computed(() =>
  filter.value ? notifications.value.filter(item => item.status === filter.value) : notifications.value,
)
const templateCodes = computed(() =>
  [...new Set(templates.value.filter(item => item.is_active).map(item => item.code))].sort(),
)

function clearMessages() {
  error.value = ''
  result.value = ''
}

async function load() {
  loading.value = true
  clearMessages()
  try {
    const [notificationResponse, ruleResponse, templateResponse, companyResponse] = await Promise.all([
      api.get<ApiResponse<Notification[]>>('/v1/notifications', {
        params: filter.value ? { status: filter.value } : {},
      }),
      api.get<ApiResponse<NotificationRule[]>>('/v1/notification-rules'),
      api.get<ApiResponse<NotificationTemplate[]>>('/v1/notification-templates'),
      api.get<ApiResponse<Company[]>>('/v1/companies'),
    ])
    notifications.value = notificationResponse.data.data
    rules.value = ruleResponse.data.data
    templates.value = templateResponse.data.data
    companies.value = companyResponse.data.data
  } catch (exception) {
    error.value = apiError(exception)
  } finally {
    loading.value = false
  }
}

async function sendTest() {
  clearMessages()
  saving.value = true
  try {
    const response = await api.post<ApiResponse<{ id: string; status: string; external_id?: string; error?: string }>>(
      '/v1/notifications/test',
      {
        ...testForm,
        company_id: testForm.company_id || null,
        subject: testForm.channel === 'EMAIL' ? testForm.subject : null,
      },
    )
    result.value = response.data.data.error || `Mensagem processada com status ${response.data.data.status}.`
    testModal.value = false
    await load()
  } catch (exception) {
    error.value = apiError(exception)
  } finally {
    saving.value = false
  }
}

function newRule() {
  Object.assign(ruleForm, {
    id: '',
    name: 'Nova régua de cobrança',
    events: [{ offset_days: -3, channels: ['EMAIL', 'WHATSAPP'], template: 'DUE_SOON' }],
    is_default: false,
    is_active: true,
  })
  ruleModal.value = true
}

function editRule(item: NotificationRule) {
  Object.assign(ruleForm, {
    id: item.id,
    name: item.name,
    events: item.events.map(event => ({ ...event, channels: [...event.channels] })),
    is_default: item.is_default,
    is_active: item.is_active,
  })
  ruleModal.value = true
}

function addRuleEvent() {
  ruleForm.events.push({ offset_days: 0, channels: ['EMAIL'], template: templateCodes.value[0] || 'DUE_TODAY' })
}

function removeRuleEvent(index: number) {
  if (ruleForm.events.length > 1) ruleForm.events.splice(index, 1)
}

function toggleEventChannel(event: RuleEvent, channel: string) {
  const index = event.channels.indexOf(channel)
  if (index >= 0) {
    if (event.channels.length > 1) event.channels.splice(index, 1)
  } else {
    event.channels.push(channel)
  }
}

async function saveRule() {
  clearMessages()
  saving.value = true
  try {
    const payload = {
      name: ruleForm.name,
      events: ruleForm.events,
      is_default: ruleForm.is_default,
      is_active: ruleForm.is_active,
    }
    if (ruleForm.id) await api.put(`/v1/notification-rules/${ruleForm.id}`, payload)
    else await api.post('/v1/notification-rules', payload)
    ruleModal.value = false
    result.value = 'Régua de cobrança salva com sucesso.'
    await load()
  } catch (exception) {
    error.value = apiError(exception)
  } finally {
    saving.value = false
  }
}

async function deactivateRule(item: NotificationRule) {
  if (item.is_default || !window.confirm(`Desativar a régua “${item.name}”?`)) return
  clearMessages()
  try {
    await api.delete(`/v1/notification-rules/${item.id}`)
    await load()
  } catch (exception) {
    error.value = apiError(exception)
  }
}

async function runRules() {
  clearMessages()
  loading.value = true
  try {
    const response = await api.post<ApiResponse<{ date: string; queued: number }>>('/v1/notification-rules/run')
    result.value = `${response.data.data.queued} comunicação(ões) colocada(s) na fila para ${response.data.data.date}.`
    tab.value = 'history'
    await load()
  } catch (exception) {
    error.value = apiError(exception)
  } finally {
    loading.value = false
  }
}

function newTemplate() {
  Object.assign(templateForm, {
    id: '',
    code: '',
    channel: 'EMAIL',
    subject: '',
    body: '',
    is_active: true,
  })
  templateModal.value = true
}

function editTemplate(item: NotificationTemplate) {
  Object.assign(templateForm, {
    id: item.id,
    code: item.code,
    channel: item.channel,
    subject: item.subject || '',
    body: item.body,
    is_active: item.is_active,
  })
  templateModal.value = true
}

async function saveTemplate() {
  clearMessages()
  saving.value = true
  try {
    const payload = {
      code: templateForm.code,
      channel: templateForm.channel,
      subject: templateForm.channel === 'EMAIL' ? templateForm.subject || null : null,
      body: templateForm.body,
      is_active: templateForm.is_active,
    }
    if (templateForm.id) await api.put(`/v1/notification-templates/${templateForm.id}`, payload)
    else await api.post('/v1/notification-templates', payload)
    templateModal.value = false
    result.value = 'Template salvo com sucesso.'
    await load()
  } catch (exception) {
    error.value = apiError(exception)
  } finally {
    saving.value = false
  }
}

async function deactivateTemplate(item: NotificationTemplate) {
  if (!window.confirm(`Desativar o template ${item.code}/${item.channel}?`)) return
  clearMessages()
  try {
    await api.delete(`/v1/notification-templates/${item.id}`)
    await load()
  } catch (exception) {
    error.value = apiError(exception)
  }
}

function offsetLabel(offset: number) {
  if (offset === 0) return 'No vencimento'
  if (offset < 0) return `${Math.abs(offset)} dia(s) antes`
  return `${offset} dia(s) depois`
}

onMounted(load)
</script>

<template>
  <PageHeader title="Comunicações" subtitle="Régua automática, templates e rastreabilidade por SMTP e Evolution API.">
    <button class="btn-secondary" :disabled="loading" @click="load">
      <RefreshCw :size="18" :class="loading ? 'animate-spin' : ''" /> Atualizar
    </button>
    <button class="btn-secondary" :disabled="loading" @click="runRules">
      <Play :size="18" /> Executar régua agora
    </button>
    <button class="btn-primary" @click="testModal = true"><Send :size="18" /> Testar envio</button>
  </PageHeader>

  <p v-if="error" class="mb-5 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{{ error }}</p>
  <p v-if="result" class="mb-5 rounded-xl bg-blue-50 p-3 text-sm text-blue-700">{{ result }}</p>

  <div class="mb-5 flex flex-wrap gap-2 rounded-2xl border border-slate-200 bg-white p-2">
    <button
      v-for="item in tabs"
      :key="item.id"
      class="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold"
      :class="tab === item.id ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-50'"
      @click="tab = item.id"
    >
      <component :is="item.icon" :size="17" /> {{ item.label }}
    </button>
  </div>

  <template v-if="tab === 'history'">
    <div class="mb-5 flex flex-wrap gap-2">
      <button
        v-for="status in ['', 'PENDING', 'RETRY', 'SENT', 'DELIVERED', 'READ', 'FAILED']"
        :key="status"
        class="rounded-full px-3 py-1.5 text-xs font-semibold"
        :class="filter === status ? 'bg-slate-900 text-white' : 'border border-slate-200 bg-white text-slate-600'"
        @click="filter = status; load()"
      >
        {{ status || 'Todos' }}
      </button>
    </div>

    <div class="table-wrap">
      <table class="table">
        <thead><tr><th>Canal</th><th>Destino</th><th>Mensagem</th><th>Tentativas</th><th>Envio</th><th>Status</th></tr></thead>
        <tbody>
          <tr v-for="item in visibleNotifications" :key="item.id">
            <td>
              <span class="inline-flex items-center gap-2 font-semibold">
                <Mail v-if="item.channel === 'EMAIL'" :size="17" class="text-blue-600" />
                <MessageCircle v-else :size="17" class="text-emerald-600" />{{ item.channel }}
              </span>
            </td>
            <td>
              <p class="font-medium">{{ item.destination }}</p>
              <p v-if="item.external_id" class="max-w-xs truncate text-xs text-slate-400">{{ item.external_id }}</p>
            </td>
            <td>
              <p>{{ item.subject || 'Mensagem WhatsApp' }}</p>
              <p class="mt-1 max-w-md truncate text-xs text-slate-400">{{ item.body.replace(/<[^>]+>/g, ' ') }}</p>
              <p v-if="item.last_error" class="mt-1 max-w-md text-xs text-rose-600">{{ item.last_error }}</p>
            </td>
            <td>{{ item.attempts }}</td>
            <td>{{ item.sent_at ? new Date(item.sent_at).toLocaleString('pt-BR') : new Date(item.scheduled_at).toLocaleString('pt-BR') }}</td>
            <td><StatusBadge :status="item.status" /></td>
          </tr>
          <tr v-if="!visibleNotifications.length"><td colspan="6" class="py-12 text-center text-slate-400">Nenhuma comunicação encontrada.</td></tr>
        </tbody>
      </table>
    </div>
  </template>

  <template v-else-if="tab === 'rules'">
    <div class="mb-4 flex justify-end"><button class="btn-primary" @click="newRule"><Plus :size="18" /> Nova régua</button></div>
    <div class="grid gap-4 xl:grid-cols-2">
      <article v-for="item in rules" :key="item.id" class="card p-5">
        <div class="flex items-start justify-between gap-4">
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="text-lg font-bold text-slate-900">{{ item.name }}</h3>
              <span v-if="item.is_default" class="rounded-full bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700">Padrão</span>
              <StatusBadge :status="item.is_active ? 'ACTIVE' : 'INACTIVE'" />
            </div>
            <p class="mt-1 text-sm text-slate-500">{{ item.events.length }} evento(s) configurado(s)</p>
          </div>
          <div class="flex gap-2">
            <button class="icon-btn" title="Editar" @click="editRule(item)"><Pencil :size="17" /></button>
            <button v-if="!item.is_default" class="icon-btn text-rose-600" title="Desativar" @click="deactivateRule(item)"><Trash2 :size="17" /></button>
          </div>
        </div>
        <div class="mt-4 space-y-2">
          <div v-for="event in item.events" :key="`${event.offset_days}-${event.template}`" class="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-slate-50 px-3 py-2 text-sm">
            <span class="font-semibold text-slate-700">{{ offsetLabel(event.offset_days) }}</span>
            <span class="text-slate-500">{{ event.template }} · {{ event.channels.join(' + ') }}</span>
          </div>
        </div>
      </article>
      <div v-if="!rules.length" class="card p-10 text-center text-slate-400">Nenhuma régua configurada.</div>
    </div>
  </template>

  <template v-else>
    <div class="mb-4 flex justify-end"><button class="btn-primary" @click="newTemplate"><Plus :size="18" /> Novo template</button></div>
    <div class="table-wrap">
      <table class="table">
        <thead><tr><th>Código</th><th>Canal</th><th>Assunto</th><th>Conteúdo</th><th>Status</th><th></th></tr></thead>
        <tbody>
          <tr v-for="item in templates" :key="item.id">
            <td class="font-semibold">{{ item.code }}</td>
            <td><span class="inline-flex items-center gap-2"><Mail v-if="item.channel === 'EMAIL'" :size="16" /><MessageCircle v-else :size="16" />{{ item.channel }}</span></td>
            <td>{{ item.subject || '—' }}</td>
            <td><p class="max-w-lg truncate text-slate-500">{{ item.body.replace(/<[^>]+>/g, ' ') }}</p></td>
            <td><StatusBadge :status="item.is_active ? 'ACTIVE' : 'INACTIVE'" /></td>
            <td><div class="flex justify-end gap-2"><button class="icon-btn" @click="editTemplate(item)"><Pencil :size="17" /></button><button v-if="item.is_active" class="icon-btn text-rose-600" @click="deactivateTemplate(item)"><Trash2 :size="17" /></button></div></td>
          </tr>
          <tr v-if="!templates.length"><td colspan="6" class="py-12 text-center text-slate-400">Nenhum template encontrado.</td></tr>
        </tbody>
      </table>
    </div>
  </template>

  <ModalDialog :open="testModal" title="Testar canal de comunicação" size="lg" @close="testModal = false">
    <form class="space-y-4" @submit.prevent="sendTest">
      <div class="grid gap-4 md:grid-cols-2">
        <div><label class="label">Canal</label><select v-model="testForm.channel" class="select"><option value="EMAIL">E-mail / SMTP</option><option value="WHATSAPP">WhatsApp / Evolution API</option></select></div>
        <div><label class="label">Empresa</label><select v-model="testForm.company_id" class="select"><option value="">Integração padrão do tenant</option><option v-for="company in companies" :key="company.id" :value="company.id">{{ company.trade_name || company.legal_name }}</option></select></div>
      </div>
      <div><label class="label">Destino</label><input v-model="testForm.destination" class="input" :placeholder="testForm.channel === 'EMAIL' ? 'financeiro@cliente.com.br' : '5575999999999'" required /></div>
      <div v-if="testForm.channel === 'EMAIL'"><label class="label">Assunto</label><input v-model="testForm.subject" class="input" required /></div>
      <div><label class="label">Mensagem</label><textarea v-model="testForm.body" class="input min-h-36" required /></div>
      <div class="flex justify-end gap-2"><button type="button" class="btn-secondary" @click="testModal = false">Cancelar</button><button class="btn-primary" :disabled="saving"><Send :size="18" /> Enviar teste</button></div>
    </form>
  </ModalDialog>

  <ModalDialog :open="ruleModal" :title="ruleForm.id ? 'Editar régua' : 'Nova régua de cobrança'" size="xl" @close="ruleModal = false">
    <form class="space-y-5" @submit.prevent="saveRule">
      <div><label class="label">Nome</label><input v-model="ruleForm.name" class="input" required /></div>
      <div class="flex flex-wrap gap-5">
        <label class="inline-flex items-center gap-2 text-sm font-medium"><input v-model="ruleForm.is_default" type="checkbox" /> Régua padrão</label>
        <label class="inline-flex items-center gap-2 text-sm font-medium"><input v-model="ruleForm.is_active" type="checkbox" /> Ativa</label>
      </div>
      <div>
        <div class="mb-3 flex items-center justify-between"><div><h4 class="font-bold text-slate-900">Eventos</h4><p class="text-xs text-slate-500">Valores negativos ocorrem antes; positivos, após o vencimento.</p></div><button type="button" class="btn-secondary" @click="addRuleEvent"><Plus :size="17" /> Evento</button></div>
        <div class="space-y-3">
          <div v-for="(event, index) in ruleForm.events" :key="index" class="grid gap-3 rounded-xl border border-slate-200 p-3 lg:grid-cols-[140px_1fr_220px_42px]">
            <div><label class="label">Offset em dias</label><input v-model.number="event.offset_days" class="input" type="number" min="-365" max="365" required /></div>
            <div><label class="label">Template</label><select v-model="event.template" class="select" required><option v-for="code in templateCodes" :key="code" :value="code">{{ code }}</option></select></div>
            <div><label class="label">Canais</label><div class="flex h-11 items-center gap-3 rounded-xl border border-slate-200 px-3"><label class="inline-flex items-center gap-1 text-sm"><input type="checkbox" :checked="event.channels.includes('EMAIL')" @change="toggleEventChannel(event, 'EMAIL')" /> E-mail</label><label class="inline-flex items-center gap-1 text-sm"><input type="checkbox" :checked="event.channels.includes('WHATSAPP')" @change="toggleEventChannel(event, 'WHATSAPP')" /> WhatsApp</label></div></div>
            <button type="button" class="icon-btn mt-6 text-rose-600" :disabled="ruleForm.events.length === 1" @click="removeRuleEvent(index)"><Trash2 :size="17" /></button>
          </div>
        </div>
      </div>
      <div class="flex justify-end gap-2"><button type="button" class="btn-secondary" @click="ruleModal = false">Cancelar</button><button class="btn-primary" :disabled="saving"><Save :size="18" /> Salvar régua</button></div>
    </form>
  </ModalDialog>

  <ModalDialog :open="templateModal" :title="templateForm.id ? 'Editar template' : 'Novo template'" size="xl" @close="templateModal = false">
    <form class="space-y-4" @submit.prevent="saveTemplate">
      <div class="grid gap-4 md:grid-cols-2">
        <div><label class="label">Código</label><input v-model="templateForm.code" class="input uppercase" placeholder="DUE_SOON" required /></div>
        <div><label class="label">Canal</label><select v-model="templateForm.channel" class="select"><option value="EMAIL">E-mail / SMTP</option><option value="WHATSAPP">WhatsApp / Evolution API</option></select></div>
      </div>
      <div v-if="templateForm.channel === 'EMAIL'"><label class="label">Assunto</label><input v-model="templateForm.subject" class="input" /></div>
      <div><label class="label">Conteúdo</label><textarea v-model="templateForm.body" class="input min-h-56 font-mono text-sm" required /></div>
      <p class="rounded-xl bg-slate-50 p-3 text-xs text-slate-600">Variáveis: <code v-pre>{{ cliente.nome }}</code>, <code v-pre>{{ empresa.nome }}</code>, <code v-pre>{{ cobranca.valor }}</code>, <code v-pre>{{ cobranca.saldo }}</code>, <code v-pre>{{ cobranca.vencimento }}</code>, <code v-pre>{{ cobranca.documento }}</code> e <code v-pre>{{ cobranca.instrucoes }}</code>.</p>
      <label class="inline-flex items-center gap-2 text-sm font-medium"><input v-model="templateForm.is_active" type="checkbox" /> Template ativo</label>
      <div class="flex justify-end gap-2"><button type="button" class="btn-secondary" @click="templateModal = false">Cancelar</button><button class="btn-primary" :disabled="saving"><Save :size="18" /> Salvar template</button></div>
    </form>
  </ModalDialog>
</template>
