import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api, sessionStorageKey } from '../api/client'
import type { ApiResponse, AuthSession } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const session = ref<AuthSession | null>(null)
  const loading = ref(false)

  const controlHost = String(import.meta.env.VITE_CONTROL_PLANE_HOST || 'control.localhost').toLowerCase()
  const isControlPlane = computed(() => {
    const host = window.location.hostname.toLowerCase()
    return host === controlHost || host.startsWith('control.') || new URLSearchParams(location.search).get('control') === '1'
  })
  const authenticated = computed(() => Boolean(session.value?.tokens.access_token))
  const user = computed(() => session.value?.user ?? null)

  function hydrate() {
    const raw = localStorage.getItem(sessionStorageKey())
    if (!raw) return
    try { session.value = JSON.parse(raw) as AuthSession } catch { localStorage.removeItem(sessionStorageKey()) }
  }

  async function login(email: string, password: string) {
    loading.value = true
    try {
      const endpoint = isControlPlane.value ? '/control/v1/auth/login' : '/v1/auth/login'
      const response = await api.post<ApiResponse<AuthSession>>(endpoint, { email, password })
      session.value = response.data.data
      localStorage.setItem(sessionStorageKey(), JSON.stringify(session.value))
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    const current = session.value
    try {
      if (current?.tokens.refresh_token) {
        const endpoint = isControlPlane.value ? '/control/v1/auth/logout' : '/v1/auth/logout'
        await api.post(endpoint, { refresh_token: current.tokens.refresh_token })
      }
    } finally {
      session.value = null
      localStorage.removeItem(sessionStorageKey())
    }
  }

  return { session, user, authenticated, loading, isControlPlane, hydrate, login, logout }
})
