import { defineStore } from 'pinia'
import { receptionApi, type Guest } from '@/api/reception'

interface State {
  guests: Guest[]
  loading: boolean
  error: string | null
}

export const useGuestsStore = defineStore('guests', {
  state: (): State => ({ guests: [], loading: false, error: null }),
  actions: {
    async load() {
      this.loading = true
      this.error = null
      try {
        this.guests = await receptionApi.listGuests()
      } catch (e: unknown) {
        const err = e as { response?: { status?: number; data?: { message?: string } }; message?: string }
        if (err.response?.status === 403) {
          this.guests = []
        } else {
          this.error = err.response?.data?.message ?? err.message ?? 'failed to load guests'
        }
      } finally {
        this.loading = false
      }
    },
    removeById(guestId: string) {
      this.guests = this.guests.filter((g) => g.id !== guestId)
    }
  }
})
