import { defineStore } from 'pinia'
import { authApi, type MeResponse, type Role } from '@/api/auth'

interface State {
  token: string | null
  user: MeResponse | null
}

export const useAuthStore = defineStore('auth', {
  state: (): State => ({ token: null, user: null }),
  getters: {
    isAuthenticated: (s) => Boolean(s.token && s.user),
    role: (s): Role | null => s.user?.role ?? null
  },
  actions: {
    restoreFromStorage() {
      const t = localStorage.getItem('hotelos.token')
      const u = localStorage.getItem('hotelos.user')
      if (t && u) {
        this.token = t
        try {
          this.user = JSON.parse(u)
        } catch {
          this.user = null
        }
      }
    },
    async login(phone: string, password: string) {
      const tok = await authApi.login(phone, password)
      this.token = tok.access_token
      localStorage.setItem('hotelos.token', tok.access_token)
      const me = await authApi.me()
      this.user = me
      localStorage.setItem('hotelos.user', JSON.stringify(me))
      return me
    },
    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('hotelos.token')
      localStorage.removeItem('hotelos.user')
    }
  }
})
