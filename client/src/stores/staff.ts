import { defineStore } from 'pinia'
import { authApi, type Role, type UserOut } from '@/api/auth'

interface State {
  users: UserOut[]
  loading: boolean
  error: string | null
}

export const useStaffStore = defineStore('staff', {
  state: (): State => ({ users: [], loading: false, error: null }),
  getters: {
    byRole: (s) => (role: Role) => s.users.filter((u) => u.role === role),
    counts: (s) => {
      const c: Record<Role, number> = { manager: 0, reception: 0, technician: 0, cleaner: 0 }
      for (const u of s.users) c[u.role] += 1
      return c
    }
  },
  actions: {
    async load(role?: Role) {
      this.loading = true
      this.error = null
      try {
        this.users = await authApi.listUsers(role)
      } catch (e: unknown) {
        const err = e as { response?: { data?: { message?: string } }; message?: string }
        this.error = err.response?.data?.message ?? err.message ?? 'failed to load staff'
      } finally {
        this.loading = false
      }
    },
    push(user: UserOut) {
      // List endpoint sorts unspecified — prepending is fine for visibility.
      this.users.unshift(user)
    }
  }
})
