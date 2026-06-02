import { defineStore } from 'pinia'

interface Envelope {
  event: string
  channel?: string
  payload?: Record<string, unknown>
  version?: number
  occurred_at?: string
}

interface State {
  socket: WebSocket | null
  connected: boolean
  lastEvent: Envelope | null
  eventLog: Envelope[]
}

const WS_URL = import.meta.env.VITE_WS_URL || '/ws'
const MAX_LOG = 100

export const useWsStore = defineStore('ws', {
  state: (): State => ({ socket: null, connected: false, lastEvent: null, eventLog: [] }),
  actions: {
    connect(token: string) {
      if (this.socket) return
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const url = `${proto}://${location.host}${WS_URL}?token=${encodeURIComponent(token)}`
      const s = new WebSocket(url)
      this.socket = s

      s.onopen = () => (this.connected = true)
      s.onclose = () => {
        this.connected = false
        this.socket = null
      }
      s.onmessage = (e) => {
        try {
          const env = JSON.parse(e.data) as Envelope
          this.lastEvent = env
          this.eventLog.unshift(env)
          if (this.eventLog.length > MAX_LOG) this.eventLog.length = MAX_LOG
        } catch {
          /* ignore */
        }
      }
    },
    disconnect() {
      this.socket?.close()
      this.socket = null
      this.connected = false
    }
  }
})
