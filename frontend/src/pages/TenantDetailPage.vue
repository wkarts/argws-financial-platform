<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ExternalLink, Globe2, Pencil, Plus, RefreshCw, RotateCcw, Settings2 } from 'lucide-vue-next'
import { api, apiError } from '../api/client'
import type { ApiResponse, PlatformPlan, Tenant } from '../types'
import PageHeader from '../components/PageHeader.vue'
import StatusBadge from '../components/StatusBadge.vue'
import ModalDialog from '../components/ModalDialog.vue'
import InlineAlert from '../components/InlineAlert.vue'

const route = useRoute()
const router = useRouter()
const tenant = ref<Tenant | null>(null)
const plans = ref<PlatformPlan[]>([])
const error = ref('')
const success = ref('')
const domainModal = ref(false)
const settingsModal = ref(false)
const hostname = ref('')
const primary = ref(false)
const retrying = ref(false)
const saving = ref(false)

const settingsForm = reactive({
  name: '',
  status: 'ACTIVE',
  plan_code: '',
  timezone: 'America/Bahia',
  demo_mode: false,
  landing_mode: 'DISABLED',
  landing_url: '',
  landing_title: '',
  landing_subtitle: '',
  landing_cta_label: 'Acessar área financeira',
  landing_cta_url: '/login',
  whatsapp_enabled: true,
  whatsapp_billing_mode: 'INCLUDED',
  whatsapp_monthly_price: '',
  custom_integrations_allowed: true,
})

const features = computed(() => tenant.value?.features || {})
const demoMode = computed(() => Boolean(features.value.demo_mode))
const landingMode = computed(() => String(features.value.landing_mode || 'DISABLED'))
const whatsappEnabled = computed(() => features.value.whatsapp_enabled !== false)
const whatsappBilling = computed(() => String(features.value.whatsapp_billing_mode || 'INCLUDED'))
const tenantPlanName = computed(() => {
  const current = tenant.value
  if (!current) return '—'
  return plans.value.find(plan => plan.code === current.plan_code)?.name || current.plan_code
})

async function load() {
  error.value = ''
  try {
    const [tenantResponse, planResponse] = await Promise.all([
      api.get<ApiResponse<Tenant>>(`/control/v1/tenants/${route.params.id}`),
      api.get<ApiResponse<PlatformPlan[]>>('/control/v1/plans', { params: { include_inactive: true } }),
    ])
    tenant.value = tenantResponse.data.data
    plans.value = planResponse.data.data
  } catch (e) {
    error.value = apiError(e)
  }
}

function openSettings() {
  if (!tenant.value) return
  const current = tenant.value.features || {}
  Object.assign(settingsForm, {
    name: tenant.value.name,
    status: tenant.value.status,
    plan_code: tenant.value.plan_code,
    timezone: tenant.value.timezone,
    demo_mode: Boolean(current.demo_mode),
    landing_mode: String(current.landing_mode || 'DISABLED'),
    landing_url: String(current.landing_url || ''),
    landing_title: String(current.landing_title || tenant.value.name || ''),
    landing_subtitle: String(current.landing_subtitle || ''),
    landing_cta_label: String(current.landing_cta_label || 'Acessar área financeira'),
    landing_cta_url: String(current.landing_cta_url || '/login'),
    whatsapp_enabled: current.whatsapp_enabled !== false,
    whatsapp_billing_mode: String(current.whatsapp_billing_mode || 'INCLUDED'),
    whatsapp_monthly_price: current.whatsapp_monthly_price == null ? '' : String(current.whatsapp_monthly_price),
    custom_integrations_allowed: current.custom_integrations_allowed !== false,
  })
  settingsModal.value = true
}

async function saveSettings() {
  if (!tenant.value || saving.value) return
  saving.value = true
  error.value = ''
  try {
    const mergedFeatures = {
      ...(tenant.value.features || {}),
      demo_mode: settingsForm.demo_mode,
      landing_mode: settingsForm.landing_mode,
      landing_url: settingsForm.landing_mode === 'EXTERNAL' ? settingsForm.landing_url.trim() : '',
      landing_title: settingsForm.landing_title.trim(),
      landing_subtitle: settingsForm.landing_subtitle.trim(),
      landing_cta_label: settingsForm.landing_cta_label.trim(),
      landing_cta_url: settingsForm.landing_cta_url.trim() || '/login',
      whatsapp_enabled: settingsForm.whatsapp_enabled,
      whatsapp_billing_mode: settingsForm.whatsapp_billing_mode,
      whatsapp_monthly_price:
        settingsForm.whatsapp_billing_mode === 'ADDON' && settingsForm.whatsapp_monthly_price !== ''
          ? Number(settingsForm.whatsapp_monthly_price)
          : null,
      custom_integrations_allowed: settingsForm.custom_integrations_allowed,
    }
    await api.patch(`/control/v1/tenants/${tenant.value.id}`, {
      name: settingsForm.name,
      status: settingsForm.status,
      plan_code: settingsForm.plan_code,
      timezone: settingsForm.timezone,
      features: mergedFeatures,
    })
    settingsModal.value = false
    success.value = 'Configurações do tenant atualizadas.'
    await load()
  } catch (e) {
    error.value = apiError(e)
  } finally {
    saving.value = false
  }
}

async function addDomain() {
  error.value = ''
  try {
    await api.post(`/control/v1/tenants/${route.params.id}/domains`, { hostname: hostname.value, is_primary: primary.value })
    domainModal.value = false
    hostname.value = ''
    success.value = 'Domínio cadastrado.'
    await load()
  } catch (e) {
    error.value = apiError(e)
  }
}

async function verify(id: string) {
  error.value = ''
  try {
    await api.post(`/control/v1/domains/${id}/verify`)
    await load()
  } catch (e) {
    error.value = apiError(e)
  }
}

async function retry() {
  if (retrying.value) return
  retrying.value = true
  error.value = ''
  try {
    const response = await api.post<ApiResponse<{ job_id: string; status: string }>>(`/control/v1/tenants/${route.params.id}/provision`)
    await router.push({ path: '/provisioning', query: { job: response.data.data.job_id, tenant: String(route.params.id) } })
  } catch (e) {
    error.value = apiError(e)
  } finally {
    retrying.value = false
  }
}

onMounted(load)
</script>

<template>
  <PageHeader :title="tenant?.name || 'Tenant'" :subtitle="tenant ? `${tenant.slug} · ${tenant.plan_code}` : 'Carregando…'">
    <button class="btn-secondary" @click="openSettings"><Settings2 :size="17" /> Configurar</button>
    <button class="btn-secondary" :disabled="retrying" @click="retry"><RotateCcw :size="17" :class="retrying && 'animate-spin'" /> {{ retrying ? 'Reprocessando…' : 'Reprocessar' }}</button>
    <button class="btn-primary" @click="domainModal=true"><Plus :size="17" /> Domínio</button>
  </PageHeader>

  <InlineAlert :message="error" @dismiss="error=''" />
  <InlineAlert :message="success" type="success" @dismiss="success=''" />

  <template v-if="tenant">
    <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
      <div class="card"><p class="text-xs text-slate-500">Status</p><div class="mt-2"><StatusBadge :status="tenant.status" /></div></div>
      <div class="card"><p class="text-xs text-slate-500">Plano</p><p class="mt-2 text-sm font-semibold">{{ tenantPlanName }}</p></div>
      <div class="card"><p class="text-xs text-slate-500">Demonstração</p><p class="mt-2 text-sm font-semibold" :class="demoMode?'text-amber-700':'text-emerald-700'">{{ demoMode ? 'Ativa' : 'Desativada' }}</p></div>
      <div class="card"><p class="text-xs text-slate-500">Landing page</p><p class="mt-2 text-sm font-semibold">{{ landingMode==='DISABLED'?'Desativada':landingMode==='EXTERNAL'?'Externa':'Gerenciada' }}</p></div>
      <div class="card"><p class="text-xs text-slate-500">WhatsApp</p><p class="mt-2 text-sm font-semibold" :class="whatsappEnabled?'text-emerald-700':'text-slate-500'">{{ whatsappEnabled ? (whatsappBilling==='ADDON'?'Adicional':'Incluído') : 'Desativado' }}</p></div>
      <div class="card"><p class="text-xs text-slate-500">Criado</p><p class="mt-2 text-sm font-semibold">{{ new Date(tenant.created_at).toLocaleDateString('pt-BR') }}</p></div>
    </div>

    <section class="mt-5">
      <div class="mb-2.5 flex items-center justify-between gap-3"><h2 class="text-base font-semibold">Domínios</h2><button class="inline-flex items-center gap-1 text-xs font-semibold text-teal-700" @click="openSettings"><Pencil :size="14"/>Editar operação e landing</button></div>
      <div class="table-wrap"><table class="table"><thead><tr><th>Hostname</th><th>Tipo</th><th>DNS</th><th>SSL</th><th></th></tr></thead><tbody><tr v-for="domain in tenant.domains" :key="domain.id"><td><div class="flex items-center gap-2"><Globe2 :size="15" class="shrink-0 text-slate-400"/><span class="max-w-[280px] truncate font-medium">{{ domain.hostname }}</span><span v-if="domain.is_primary" class="badge bg-blue-100 text-blue-700">Principal</span></div></td><td>{{ domain.domain_type }}</td><td><StatusBadge :status="domain.status" /></td><td><StatusBadge :status="domain.ssl_status" /></td><td><div class="flex items-center gap-2"><a :href="`https://${domain.hostname}`" target="_blank" rel="noopener" class="btn-secondary !min-h-8 !px-2.5 !py-1.5"><ExternalLink :size="14"/>Abrir</a><button v-if="domain.domain_type === 'CUSTOM'" class="btn-secondary !min-h-8 !px-2.5 !py-1.5" @click="verify(domain.id)"><RefreshCw :size="14"/> Verificar</button><span v-else class="text-xs font-medium text-slate-400">Gerenciado</span></div></td></tr></tbody></table></div>
    </section>
  </template>

  <ModalDialog :open="settingsModal" title="Configurar tenant" size="xl" @close="settingsModal=false">
    <form class="space-y-6" @submit.prevent="saveSettings">
      <section>
        <h3 class="mb-3 font-semibold text-slate-900">Operação</h3>
        <div class="grid gap-4 md:grid-cols-2">
          <div><label class="label">Nome</label><input v-model="settingsForm.name" class="input" required/></div>
          <div><label class="label">Plano</label><select v-model="settingsForm.plan_code" class="select" required><option v-for="plan in plans" :key="plan.code" :value="plan.code">{{plan.name}}{{plan.is_active?'':' · inativo'}}</option></select></div>
          <div><label class="label">Status</label><select v-model="settingsForm.status" class="select"><option value="ACTIVE">Ativo</option><option value="SUSPENDED">Suspenso</option><option value="BLOCKED">Bloqueado</option><option value="CANCELLED">Cancelado</option></select></div>
          <div><label class="label">Fuso horário</label><input v-model="settingsForm.timezone" class="input" placeholder="America/Bahia"/></div>
        </div>
        <label class="mt-4 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm"><input v-model="settingsForm.demo_mode" type="checkbox" class="mt-0.5"/><span><strong>Modo demonstração</strong><span class="mt-1 block text-amber-800">Use apenas em ambientes de apresentação. Desative quando o tenant entrar em operação real.</span></span></label>
      </section>

      <section class="border-t pt-5">
        <h3 class="mb-1 font-semibold text-slate-900">Landing page</h3>
        <p class="mb-4 text-sm text-slate-500">Defina se o domínio utiliza a landing gerenciada pela plataforma, uma página externa ou nenhuma landing.</p>
        <div class="grid gap-4 md:grid-cols-2">
          <div><label class="label">Modo</label><select v-model="settingsForm.landing_mode" class="select"><option value="DISABLED">Sem landing pública</option><option value="PLATFORM">Landing gerenciada pela plataforma</option><option value="EXTERNAL">Associar landing externa</option></select></div>
          <div v-if="settingsForm.landing_mode==='EXTERNAL'"><label class="label">URL da landing externa</label><input v-model="settingsForm.landing_url" type="url" class="input" placeholder="https://www.cliente.com.br" required/></div>
          <template v-if="settingsForm.landing_mode==='PLATFORM'">
            <div><label class="label">Título</label><input v-model="settingsForm.landing_title" class="input"/></div>
            <div><label class="label">Subtítulo</label><input v-model="settingsForm.landing_subtitle" class="input"/></div>
            <div><label class="label">Texto do botão</label><input v-model="settingsForm.landing_cta_label" class="input"/></div>
            <div><label class="label">Destino do botão</label><input v-model="settingsForm.landing_cta_url" class="input" placeholder="/login"/></div>
          </template>
        </div>
      </section>

      <section class="border-t pt-5">
        <h3 class="mb-1 font-semibold text-slate-900">WhatsApp da plataforma</h3>
        <p class="mb-4 text-sm text-slate-500">Controle comercial do recurso oferecido pela própria ARGWS. O tenant não recebe credenciais nem informações do provedor interno.</p>
        <div class="grid gap-4 md:grid-cols-2">
          <label class="flex items-center gap-2 rounded-xl border border-slate-200 p-3 text-sm"><input v-model="settingsForm.whatsapp_enabled" type="checkbox"/> WhatsApp habilitado para este tenant</label>
          <label class="flex items-center gap-2 rounded-xl border border-slate-200 p-3 text-sm"><input v-model="settingsForm.custom_integrations_allowed" type="checkbox"/> Permitir integrações personalizadas</label>
          <div><label class="label">Modelo comercial</label><select v-model="settingsForm.whatsapp_billing_mode" class="select" :disabled="!settingsForm.whatsapp_enabled"><option value="INCLUDED">Incluído no plano</option><option value="ADDON">Adicional cobrado separadamente</option></select></div>
          <div v-if="settingsForm.whatsapp_billing_mode==='ADDON'"><label class="label">Valor mensal do adicional</label><input v-model="settingsForm.whatsapp_monthly_price" type="number" min="0" step="0.01" class="input"/></div>
        </div>
      </section>

      <div class="flex justify-end gap-2 border-t pt-4"><button type="button" class="btn-secondary" @click="settingsModal=false">Cancelar</button><button class="btn-primary" :disabled="saving">{{saving?'Salvando…':'Salvar configurações'}}</button></div>
    </form>
  </ModalDialog>

  <ModalDialog :open="domainModal" title="Adicionar domínio personalizado" @close="domainModal=false">
    <form class="space-y-3" @submit.prevent="addDomain">
      <div><label class="label">Hostname completo</label><input v-model="hostname" class="input" placeholder="financeiro.cliente.com.br" required /><p class="mt-1.5 text-xs leading-5 text-slate-500">Configure um CNAME apontando para o gateway informado pela plataforma.</p></div>
      <label class="flex items-center gap-2 text-sm"><input v-model="primary" type="checkbox"/> Tornar domínio principal</label>
      <div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end"><button type="button" class="btn-secondary" @click="domainModal=false">Cancelar</button><button class="btn-primary">Cadastrar</button></div>
    </form>
  </ModalDialog>
</template>
