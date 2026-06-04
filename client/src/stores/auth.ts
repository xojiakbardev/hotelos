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
    role: (s): Role | null => s.user?.role ?? null,
    isGuest: (s): boolean => s.user?.role === 'guest',
    mustChangePassword: (s): boolean => s.user?.must_change_password ?? false
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
      if (tok.role === 'guest') {
        const me: MeResponse = {
          id: tok.user_id,
          phone: tok.phone,
          full_name: tok.full_name,
          role: tok.role,
          is_active: true,
          must_change_password: tok.must_change_password ?? false,
          guest_id: tok.guest_id,
          room_id: tok.room_id,
          room_number: tok.room_number,
        }
        this.user = me
        localStorage.setItem('hotelos.user', JSON.stringify(me))
        return me
      }
      const me = await authApi.me()
      this.user = me
      localStorage.setItem('hotelos.user', JSON.stringify(me))
      return me
    },
    async changePassword(currentPassword: string, newPassword: string) {
      const tok = await authApi.changePassword(currentPassword, newPassword)
      this.token = tok.access_token
      localStorage.setItem('hotelos.token', tok.access_token)
      if (this.user) {
        this.user.must_change_password = false
        localStorage.setItem('hotelos.user', JSON.stringify(this.user))
      }
    },
    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('hotelos.token')
      localStorage.removeItem('hotelos.user')
    }
  }
})
