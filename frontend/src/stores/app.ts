import { ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../api/client'
import type { ApiResponse } from '../types'

interface TenantContextData {
  tenant_id: string
  slug: string
  hostname: string
  timezone: string
  branding: {
    name: string
    logo_url?: string
    favicon_url?: string
    primary_color: string
    secondary_color: string
  }
}

interface PublicSiteData {
  demo_mode: boolean
}

export const useAppStore = defineStore('app', () => {
  const tenant = ref<TenantContextData | null>(null)
  const demoMode = ref(false)
  const sidebarOpen = ref(false)
  const globalLoading = ref(false)

  async function loadTenantContext() {
    try {
      const response = await api.get<ApiResponse<TenantContextData>>('/v1/context')
      tenant.value = response.data.data
      document.title = response.data.data.branding.name || 'Financeiro'
      document.documentElement.style.setProperty('--brand-primary', response.data.data.branding.primary_color)
      document.documentElement.style.setProperty('--brand-secondary', response.data.data.branding.secondary_color)
      const manifest = document.querySelector<HTMLLinkElement>('#app-manifest')
      if (manifest) manifest.href = '/api/v1/manifest.webmanifest'
    } catch {
      tenant.value = null
    }

    try {
      const siteResponse = await api.get<ApiResponse<PublicSiteData>>('/v1/public/site')
      demoMode.value = Boolean(siteResponse.data.data.demo_mode)
    } catch {
      demoMode.value = false
    }
  }

  return { tenant, demoMode, sidebarOpen, globalLoading, loadTenantContext }
})
