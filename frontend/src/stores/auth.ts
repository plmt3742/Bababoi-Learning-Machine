import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as authApi from '../api/auth'
import { clearAuthToken, getAuthToken, setAuthToken } from '../api/authToken'
import { normalizeApiError } from '../api/errors'
import type { AuthResponse, LoginPayload, RegisterPayload, User } from '../api/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getAuthToken())
  const user = ref<User | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => token.value !== null)

  function applySession(response: AuthResponse): void {
    token.value = response.access_token
    setAuthToken(response.access_token)
    user.value = response.user
    error.value = null
  }

  function clearSession(): void {
    token.value = null
    user.value = null
    error.value = null
    clearAuthToken()
  }

  async function login(payload: LoginPayload): Promise<User> {
    loading.value = true
    error.value = null

    try {
      const response = await authApi.login(payload)
      applySession(response)
      return response.user
    } catch (cause) {
      const apiError = normalizeApiError(cause)
      error.value = apiError.message
      throw apiError
    } finally {
      loading.value = false
    }
  }

  async function register(payload: RegisterPayload): Promise<User> {
    loading.value = true
    error.value = null

    try {
      const response = await authApi.register(payload)
      applySession(response)
      return response.user
    } catch (cause) {
      const apiError = normalizeApiError(cause)
      error.value = apiError.message
      throw apiError
    } finally {
      loading.value = false
    }
  }

  async function fetchMe(): Promise<User | null> {
    token.value = getAuthToken()
    if (!token.value) {
      user.value = null
      return null
    }

    loading.value = true
    try {
      const currentUser = await authApi.me()
      user.value = currentUser
      return currentUser
    } catch (cause) {
      const apiError = normalizeApiError(cause)
      if (apiError.status === 401) clearSession()
      else error.value = apiError.message
      throw apiError
    } finally {
      loading.value = false
    }
  }

  function logout(): void {
    clearSession()
  }

  /** Boot-time restore: keep a valid token, drop one the backend rejects. */
  async function restore(): Promise<void> {
    token.value = getAuthToken()
    if (!token.value) {
      user.value = null
      return
    }

    try {
      await fetchMe()
    } catch {
      // fetchMe clears auth on 401 and stores a friendly message otherwise.
    }
  }

  function clearError(): void {
    error.value = null
  }

  return {
    token,
    user,
    isAuthenticated,
    loading,
    error,
    login,
    register,
    fetchMe,
    logout,
    restore,
    clearError,
  }
})
