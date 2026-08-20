import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { ApiResponse, AuthSession, TokenPair } from '../types'

const hostKey = () => `argws-financial-session:${window.location.hostname}`
const controlHost = String(import.meta.env.VITE_CONTROL_PLANE_HOST || 'control.localhost').toLowerCase()

function isControlPlaneHost(): boolean {
  const host = window.location.hostname.toLowerCase()
  return host === controlHost || host.startsWith('control.') || new URLSearchParams(location.search).get('control') === '1'
}

function readSession(): AuthSession | null {
  const raw = localStorage.getItem(hostKey())
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthSession
  } catch {
    localStorage.removeItem(hostKey())
    return null
  }
}

function persistSession(session: AuthSession): void {
  localStorage.setItem(hostKey(), JSON.stringify(session))
}

function clearSessionAndRedirect(): void {
  localStorage.removeItem(hostKey())
  if (window.location.pathname !== '/login') window.location.assign('/login')
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.request.use(config => {
  const session = readSession()
  if (session?.tokens?.access_token) config.headers.Authorization = `Bearer ${session.tokens.access_token}`
  config.headers['X-Request-ID'] = crypto.randomUUID()
  return config
})

interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _argwsRetried?: boolean
}

let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  const session = readSession()
  if (!session?.tokens?.refresh_token) throw new Error('Refresh token ausente.')
  const endpoint = isControlPlaneHost() ? '/control/v1/auth/refresh' : '/v1/auth/refresh'
  const baseURL = String(api.defaults.baseURL || '/api').replace(/\/$/, '')
  const response = await axios.post<ApiResponse<TokenPair>>(
    `${baseURL}${endpoint}`,
    { refresh_token: session.tokens.refresh_token },
    { timeout: 30000, headers: { 'Content-Type': 'application/json', 'X-Request-ID': crypto.randomUUID() } }
  )
  session.tokens = response.data.data
  persistSession(session)
  return session.tokens.access_token
}

api.interceptors.response.use(
  response => response,
  async (error: AxiosError) => {
    const config = error.config as RetryableRequestConfig | undefined
    const url = String(config?.url || '')
    const isAuthOperation = ['/auth/login', '/auth/refresh', '/auth/logout'].some(path => url.includes(path))
    if (error.response?.status === 401 && config && !config._argwsRetried && !isAuthOperation) {
      config._argwsRetried = true
      try {
        refreshPromise ??= refreshAccessToken().finally(() => { refreshPromise = null })
        const accessToken = await refreshPromise
        config.headers.Authorization = `Bearer ${accessToken}`
        return api.request(config)
      } catch {
        clearSessionAndRedirect()
      }
    } else if (error.response?.status === 401 && !url.includes('/auth/login')) {
      clearSessionAndRedirect()
    }
    return Promise.reject(error)
  }
)

export function apiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { error?: { message?: string } } | undefined
    return data?.error?.message || error.message || 'Falha na comunicação com o servidor.'
  }
  return error instanceof Error ? error.message : 'Erro inesperado.'
}

export function sessionStorageKey(): string {
  return hostKey()
}
