import { defineStore } from 'pinia'
import { receptionApi, type Room } from '@/api/reception'

interface State {
  rooms: Room[]
  loading: boolean
  error: string | null
  loadedAt: number | null
}

/**
 * Rooms inventory store.
 *
 * Source of truth: the reception-service API. We re-fetch on any incoming
 * `rooms.*` or `guests.*` WebSocket event because the affected room may
 * have changed state on the server — refetching is cheap (20 rows) and
 * keeps the dashboard honest without per-event diff logic.
 */
export const useRoomsStore = defineStore('rooms', {
  state: (): State => ({ rooms: [], loading: false, error: null, loadedAt: null }),
  getters: {
    byStatus: (s) => (status: string) => s.rooms.filter((r) => r.status === status),
    available: (s) =>
      s.rooms.filter(
        (r) => r.status === 'available' && r.cleanliness_status === 'clean'
      ),
    count: (s) => s.rooms.length
  },
  actions: {
    async load() {
      this.loading = true
      this.error = null
      try {
        const res = await receptionApi.listRooms()
        this.rooms = res.rooms
        this.loadedAt = Date.now()
      } catch (e: unknown) {
        const err = e as { response?: { data?: { message?: string } }; message?: string }
        this.error = err.response?.data?.message ?? err.message ?? 'failed to load rooms'
      } finally {
        this.loading = false
      }
    },
    /** Apply an optimistic local patch. The next refetch reconciles. */
    patchLocal(roomId: string, patch: Partial<Room>) {
      const idx = this.rooms.findIndex((r) => r.id === roomId)
      if (idx === -1) return
      this.rooms[idx] = { ...this.rooms[idx], ...patch }
    }
  }
})
