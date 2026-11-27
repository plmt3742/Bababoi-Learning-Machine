import { defineStore } from 'pinia'

import { adminLogin, adminLogout, adminMe } from '../api/admin'
import type { AdminProfile } from '../types'

const TOKEN_KEY = 'bababoi:admin-token'
const USER_KEY = 'bababoi:admin-user'

function readProfile(): AdminProfile | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as AdminProfile
    if (!parsed || typeof parsed.username !== 'string') return null
    return parsed
  } catch {
    return null
  }
}

export const useAdminAuth = defineStore('admin-auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) ?? '',
    user: readProfile(),
    sessionChecked: false,
  }),
  getters: {
    isAuthenticated: (state): boolean => Boolean(state.token),
  },
  actions: {
    persist(): void {
      if (this.token) localStorage.setItem(TOKEN_KEY, this.token)
      if (this.user) localStorage.setItem(USER_KEY, JSON.stringify(this.user))
    },
    applySession(token: string, profile: AdminProfile): void {
      this.token = token
      this.user = profile
      this.sessionChecked = true
      this.persist()
    },
    clear(): void {
      this.token = ''
      this.user = null
      this.sessionChecked = true
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },
    async login(username: string, password: string): Promise<void> {
      const result = await adminLogin(username.trim(), password)
      if (result.user.role !== 'admin') {
        throw new Error('该账号没有管理端权限')
      }
      this.applySession(result.access_token, result.user)
    },
    async ensureSession(): Promise<boolean> {
      if (this.sessionChecked) return Boolean(this.token && this.user)
      this.sessionChecked = true
      if (!this.token) return false
      try {
        const profile = await adminMe()
        if (profile.role !== 'admin') {
          this.clear()
          return false
        }
        this.applySession(this.token, profile)
        return true
      } catch {
        this.clear()
        return false
      }
    },
    async logout(): Promise<void> {
      if (this.token) {
        try {
          await adminLogout()
        } catch (cause) {
          console.warn('管理端退出接口调用失败，已清理本地会话', cause)
        }
      }
      this.clear()
    },
  },
})
