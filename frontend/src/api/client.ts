import axios from 'axios'
import { clearAuthToken, getAuthToken } from './authToken'
import { ApiError, normalizeApiError } from './errors'

const DEFAULT_BASE_URL = '/api/v1'
const REQUEST_TIMEOUT_MS = 120_000
const AUTH_ENDPOINTS_WITH_OWN_401 = ['/auth/login', '/auth/register']

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_BASE_URL,
  timeout: REQUEST_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
})

export type UnauthorizedHandler = (error: ApiError) => void

let unauthorizedHandler: UnauthorizedHandler | null = null
let fallbackRedirectScheduled = false

/**
 * The Axios layer must not import stores/router (that would create a cycle).
 * main.ts registers a handler that clears Pinia state and redirects.
 */
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler
}

function isAuthEndpoint(url: string | undefined): boolean {
  if (!url) return false
  return AUTH_ENDPOINTS_WITH_OWN_401.some((path) => url === path || url.endsWith(path))
}

function redirectToLoginFallback(): void {
  if (typeof window === 'undefined' || fallbackRedirectScheduled) return
  if (window.location.pathname.endsWith('/login')) return

  fallbackRedirectScheduled = true
  const current = `${window.location.pathname}${window.location.search}${window.location.hash}`
  const loginPath = `${import.meta.env.BASE_URL.replace(/\/$/, '')}/login`
  window.location.assign(`${loginPath}?redirect=${encodeURIComponent(current)}`)
}

apiClient.interceptors.request.use((config) => {
  const token = getAuthToken()
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`)
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    const apiError = normalizeApiError(error)
    const url = axios.isAxiosError(error) ? error.config?.url : undefined

    if (apiError.status === 401 && !isAuthEndpoint(url)) {
      clearAuthToken()
      if (unauthorizedHandler) unauthorizedHandler(apiError)
      else redirectToLoginFallback()
    }

    return Promise.reject(apiError)
  },
)

export default apiClient
