import { defineStore } from 'pinia'
import { housekeepingApi, type CleaningEntry } from '@/api/housekeeping'

interface State {
  entries: CleaningEntry[]
  loading: boolean
  error: string | null
}

export const useHousekeepingStore = defineStore('housekeeping', {
  state: (): State => ({ entries: [], loading: false, error: null }),
  getters: {
    pending: (s) => s.entries.filter((e) => e.status === 'pending'),
    inProgress: (s) => s.entries.filter((e) => e.status === 'in_progress')
  },
  actions: {
    async load() {
      this.loading = true
      this.error = null
      try {
        this.entries = await housekeepingApi.listQueue()
      } catch (e: unknown) {
        const err = e as { response?: { data?: { message?: string } }; message?: string }
        this.error = err.response?.data?.message ?? err.message ?? 'failed to load queue'
      } finally {
        this.loading = false
      }
    },
    /** Replace an entry by id (used by optimistic UI flows). */
    upsert(entry: CleaningEntry) {
      const idx = this.entries.findIndex((e) => e.id === entry.id)
      if (idx === -1) this.entries.push(entry)
      else this.entries[idx] = entry
    }
  }
})
