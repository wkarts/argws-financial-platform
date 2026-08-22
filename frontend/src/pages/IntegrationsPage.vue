<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { CheckCircle2, Mail, MessageCircle, Plus, Save, ServerCog, Settings2 } from 'lucide-vue-next'
import { api, apiError } from '../api/client'
import type { ApiResponse, Company } from '../types'
import PageHeader from '../components/PageHeader.vue'
import ModalDialog from '../components/ModalDialog.vue'
import StatusBadge from '../components/StatusBadge.vue'
import InlineAlert from '../components/InlineAlert.vue'

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
interface PlatformService { label:string;managed:boolean;available:boolean;configured_by_platform:boolean;billing_mode?:string;monthly_price?:unknown }
interface PlatformServices { whatsapp:PlatformService;email:PlatformService;custom_integrations_allowed:boolean }
type ProviderPreset = { provider:string;label:string;description:string;publicFields:Array<{key:string;label:string;placeholder?:string;type?:string}>;secretFields:Array<{key:string;label:string;placeholder?:string}> }

const presets: ProviderPreset[] = [
  {provider:'EVOLUTION',label:'WhatsApp personalizado',description:'Conecte uma infraestrutura própria usando Evolution API.',publicFields:[{key:'base_url',label:'URL da Evolution API',placeholder:'https://evolution.exemplo.com.br'},{key:'instance',label:'Instância',placeholder:'financeiro'}],secretFields:[{key:'api_key',label:'API Key',placeholder:'••••••••'},{key:'webhook_secret',label:'Segredo do webhook',placeholder:'••••••••'}]},
  {provider:'SMTP',label:'E-mail personalizado',description:'Use um servidor SMTP próprio em vez do serviço padrão da plataforma.',publicFields:[{key:'host',label:'Servidor SMTP',placeholder:'smtp.seudominio.com.br'},{key:'port',label:'Porta',placeholder:'587',type:'number'},{key:'security',label:'Segurança',placeholder:'starttls'},{key:'from_name',label:'Nome do remetente',placeholder:'Financeiro'},{key:'from_email',label:'E-mail remetente',placeholder:'financeiro@dominio.com.br'}],secretFields:[{key:'username',label:'Usuário SMTP',placeholder:'financeiro@dominio.com.br'},{key:'password',label:'Senha SMTP',placeholder:'••••••••'}]},
  {provider:'NFSE',label:'NFS-e personalizada',description:'Credenciais específicas para um emissor fiscal externo.',publicFields:[{key:'provider',label:'Emissor fiscal',placeholder:'Provedor homologado'},{key:'municipality_code',label:'Código IBGE',placeholder:'2928701'},{key:'environment',label:'Ambiente',placeholder:'Homologação'}],secretFields:[{key:'certificate_password',label:'Senha do certificado',placeholder:'••••••••'},{key:'api_token',label:'Token da API',placeholder:'••••••••'}]},
  {provider:'BACKUP',label:'Backup remoto personalizado',description:'Destino adicional de backup sob responsabilidade da empresa.',publicFields:[{key:'drive_remote',label:'Destino Google Drive',placeholder:'gdrive:financeiro'},{key:'dropbox_remote',label:'Destino Dropbox',placeholder:'dropbox:financeiro'}],secretFields:[]}
]

const integrations=ref<Integration[]>([]),companies=ref<Company[]>([]),services=ref<PlatformServices|null>(null),modal=ref(false),error=ref(''),success=ref(''),selected=ref<ProviderPreset>(presets[0])
const form=reactive({scope:'TENANT',company_id:'',is_enabled:true,public_config:{} as Record<string,unknown>,secrets:{} as Record<string,string>})
const companyName=(id?:string|null)=>{if(!id)return'Todas as empresas';const item=companies.value.find(company=>company.id===id);return item?.trade_name||item?.legal_name||'Empresa'}
const billingText=(service?:PlatformService)=>{if(!service?.available)return'Indisponível para esta conta';if(service.billing_mode==='ADDON'&&service.monthly_price)return`Disponível como adicional · R$ ${Number(service.monthly_price).toLocaleString('pt-BR',{minimumFractionDigits:2})}/mês`;if(service.billing_mode==='ADDON')return'Disponível como adicional';return'Incluído na plataforma'}
const presetFor=(provider:string)=>presets.find(item=>item.provider===provider)||{provider,label:'Integração personalizada',description:'Configuração personalizada.',publicFields:[],secretFields:[]}
async function load(){error.value='';try{const [items,companyResponse,platformResponse]=await Promise.all([api.get<ApiResponse<Integration[]>>('/v1/integrations'),api.get<ApiResponse<Company[]>>('/v1/companies'),api.get<ApiResponse<PlatformServices>>('/v1/platform-services')]);integrations.value=items.data.data;companies.value=companyResponse.data.data;services.value=platformResponse.data.data}catch(exception){error.value=apiError(exception)}}
function openEditor(preset:ProviderPreset,current?:Integration){selected.value=preset;form.scope=current?.scope||'TENANT';form.company_id=current?.company_id||'';form.is_enabled=current?.is_enabled??true;form.public_config={...(current?.public_config||{})};form.secrets={};modal.value=true;error.value='';success.value=''}
function editIntegration(item:Integration){openEditor(presetFor(item.provider),item)}
async function save(){error.value='';try{const body={scope:form.company_id?'COMPANY':form.scope,company_id:form.company_id||null,is_enabled:form.is_enabled,public_config:form.public_config,secrets:Object.fromEntries(Object.entries(form.secrets).filter(([,value])=>String(value).trim()!==''))};await api.put(`/v1/integrations/${selected.value.provider}`,body);success.value=`${selected.value.label} configurado com sucesso.`;modal.value=false;await load()}catch(exception){error.value=apiError(exception)}}
onMounted(load)
</script>

<template>
  <PageHeader title="Integrações" subtitle="Serviços de comunicação fornecidos pela plataforma e integrações personalizadas opcionais." />
  <InlineAlert :message="error" @dismiss="error=''"/><InlineAlert :message="success" type="success" @dismiss="success=''"/>

  <section class="mb-8">
    <div class="mb-3"><h2 class="text-lg font-semibold">Serviços da plataforma</h2><p class="text-sm text-slate-500">Você não precisa informar API Key, servidor ou fornecedor para utilizar estes recursos.</p></div>
    <div class="grid gap-4 lg:grid-cols-2">
      <article class="card flex items-start gap-4">
        <div class="rounded-2xl bg-emerald-50 p-3 text-emerald-700"><MessageCircle :size="25"/></div>
        <div class="min-w-0 flex-1"><div class="flex flex-wrap items-center gap-2"><h3 class="font-bold">WhatsApp</h3><StatusBadge :status="services?.whatsapp.available?'ACTIVE':'INACTIVE'"/></div><p class="mt-2 text-sm leading-6 text-slate-500">Envio de mensagens de cobrança, lembretes e confirmações usando a infraestrutura gerenciada pela ARGWS.</p><p class="mt-3 text-xs font-semibold" :class="services?.whatsapp.available?'text-emerald-700':'text-amber-700'">{{billingText(services?.whatsapp)}}</p></div>
      </article>
      <article class="card flex items-start gap-4">
        <div class="rounded-2xl bg-blue-50 p-3 text-blue-700"><Mail :size="25"/></div>
        <div class="min-w-0 flex-1"><div class="flex flex-wrap items-center gap-2"><h3 class="font-bold">E-mail</h3><StatusBadge :status="services?.email.available?'ACTIVE':'INACTIVE'"/></div><p class="mt-2 text-sm leading-6 text-slate-500">Envio de documentos e comunicações financeiras pelo serviço de e-mail configurado na plataforma.</p><p class="mt-3 text-xs font-semibold" :class="services?.email.available?'text-emerald-700':'text-amber-700'">{{services?.email.available?'Gerenciado pela plataforma':'Indisponível no momento'}}</p></div>
      </article>
    </div>
  </section>

  <section v-if="services?.custom_integrations_allowed!==false">
    <div class="mb-3 flex flex-wrap items-end justify-between gap-3"><div><h2 class="text-lg font-semibold">Integrações personalizadas</h2><p class="text-sm text-slate-500">Opcional. Use somente quando sua empresa precisar de infraestrutura ou fornecedor próprio.</p></div><button class="btn-secondary" @click="openEditor(presets[0])"><Plus :size="18"/>Adicionar integração personalizada</button></div>
    <div v-if="integrations.length" class="grid gap-4 xl:grid-cols-2">
      <article v-for="item in integrations" :key="item.id" class="card"><div class="flex items-start gap-4"><div class="rounded-2xl bg-violet-50 p-3 text-violet-700"><ServerCog :size="23"/></div><div class="min-w-0 flex-1"><div class="flex flex-wrap items-center gap-2"><h3 class="font-bold">{{presetFor(item.provider).label}}</h3><StatusBadge :status="item.is_enabled?'ACTIVE':'DISABLED'"/></div><p class="mt-1 text-sm text-slate-500">{{companyName(item.company_id)}}</p><p class="mt-2 text-xs text-slate-400">Credenciais {{item.has_secrets?'protegidas e configuradas':'ainda não informadas'}}</p><p v-if="item.last_health_status" class="mt-1 text-xs text-slate-400">Verificação: {{item.last_health_status==='HEALTHY'?'Funcionando':'Requer atenção'}}</p><button class="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-teal-700" @click="editIntegration(item)"><Settings2 :size="15"/>Editar configuração</button></div></div></article>
    </div>
    <div v-else class="rounded-xl border border-dashed border-slate-200 bg-white p-8 text-center"><CheckCircle2 class="mx-auto text-emerald-600" :size="28"/><p class="mt-3 font-semibold">Nenhuma integração personalizada necessária</p><p class="mt-1 text-sm text-slate-500">Os serviços gerenciados pela plataforma podem ser utilizados sem configuração técnica nesta área.</p></div>
  </section>

  <ModalDialog :open="modal" title="Integração personalizada" size="lg" @close="modal=false">
    <form class="space-y-5" @submit.prevent="save">
      <div><label class="label">Tipo de integração</label><select v-model="selected" class="select" @change="form.public_config={};form.secrets={}"><option v-for="preset in presets" :key="preset.provider" :value="preset">{{preset.label}}</option></select><p class="mt-2 text-sm text-slate-500">{{selected.description}}</p></div>
      <div class="grid gap-4 md:grid-cols-2"><div><label class="label">Aplicar em</label><select v-model="form.scope" class="select"><option value="TENANT">Todas as empresas</option><option value="COMPANY">Empresa específica</option></select></div><div><label class="label">Empresa</label><select v-model="form.company_id" class="select"><option value="">Todas as empresas</option><option v-for="company in companies" :key="company.id" :value="company.id">{{company.trade_name||company.legal_name}}</option></select></div></div>
      <div class="grid gap-4 md:grid-cols-2"><div v-for="field in selected.publicFields" :key="field.key"><label class="label">{{field.label}}</label><input v-model="form.public_config[field.key]" :type="field.type||'text'" :placeholder="field.placeholder" class="input"/></div></div>
      <div v-if="selected.secretFields.length" class="rounded-2xl border border-amber-200 bg-amber-50 p-4"><p class="mb-1 text-sm font-semibold text-amber-900">Credenciais da integração personalizada</p><p class="mb-3 text-xs text-amber-800">Os valores são criptografados no servidor e não são exibidos novamente.</p><div class="grid gap-4 md:grid-cols-2"><div v-for="field in selected.secretFields" :key="field.key"><label class="label">{{field.label}}</label><input v-model="form.secrets[field.key]" type="password" :placeholder="field.placeholder" class="input" autocomplete="new-password"/></div></div></div>
      <label class="flex items-center gap-2 text-sm font-medium text-slate-700"><input v-model="form.is_enabled" type="checkbox"/> Integração habilitada</label>
      <div class="flex justify-end gap-2"><button type="button" class="btn-secondary" @click="modal=false">Cancelar</button><button class="btn-primary"><Save :size="18"/>Salvar</button></div>
    </form>
  </ModalDialog>
</template>
