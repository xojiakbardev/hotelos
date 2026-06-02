import { defineStore } from 'pinia'
import { receptionApi, type Order } from '@/api/reception'

interface State {
  orders: Order[]
  loading: boolean
  error: string | null
}

export const useOrdersStore = defineStore('orders', {
  state: (): State => ({ orders: [], loading: false, error: null }),
  getters: {
    open: (s) => s.orders.filter((o) => o.status !== 'delivered'),
    delivered: (s) => s.orders.filter((o) => o.status === 'delivered')
  },
  actions: {
    async load() {
      this.loading = true
      this.error = null
      try {
        this.orders = await receptionApi.listOrders()
      } catch (e: unknown) {
        const err = e as { response?: { data?: { message?: string } }; message?: string }
        this.error = err.response?.data?.message ?? err.message ?? 'failed to load orders'
      } finally {
        this.loading = false
      }
    },
    upsert(order: Order) {
      const idx = this.orders.findIndex((o) => o.id === order.id)
      if (idx === -1) this.orders.unshift(order)
      else this.orders[idx] = order
    }
  }
})
