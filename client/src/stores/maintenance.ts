import { defineStore } from 'pinia'
import { maintenanceApi, type Issue } from '@/api/maintenance'

interface State {
  open: Issue[]
  mine: Issue[]
  loading: boolean
  error: string | null
}

export const useMaintenanceStore = defineStore('maintenance', {
  state: (): State => ({ open: [], mine: [], loading: false, error: null }),
  getters: {
    unassigned: (s) => s.open.filter((i) => i.status === 'reported'),
    assigned: (s) => s.open.filter((i) => i.status === 'assigned')
  },
  actions: {
    async load() {
      this.loading = true
      this.error = null
      try {
        const [open, mine] = await Promise.all([
          maintenanceApi.queue(),
          maintenanceApi.myQueue().catch(() => [] as Issue[])
        ])
        this.open = open
        this.mine = mine
      } catch (e: unknown) {
        // Silently handle 403 — means role doesn't have access
        const err = e as { response?: { status?: number; data?: { message?: string } }; message?: string }
        if (err.response?.status === 403) {
          this.open = []
          this.mine = []
        } else {
          this.error = err.response?.data?.message ?? err.message ?? 'failed to load issues'
        }
      } finally {
        this.loading = false
      }
    },
    upsert(issue: Issue) {
      const replace = (arr: Issue[]) => {
        const i = arr.findIndex((x) => x.id === issue.id)
        if (i === -1) arr.push(issue)
        else arr[i] = issue
        return arr
      }
      this.open = replace([...this.open])
      this.mine = replace([...this.mine])
    },
    removeById(issueId: string) {
      this.open = this.open.filter((i) => i.id !== issueId)
      this.mine = this.mine.filter((i) => i.id !== issueId)
    }
  }
})
