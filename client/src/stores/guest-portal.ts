import { defineStore } from 'pinia'
import {
  guestPortalApi,
  type GuestCleaning,
  type GuestDashboard,
  type GuestMaintenance,
  type GuestOrder,
  type GuestOrderItem
} from '@/api/guest-portal'

interface State {
  guestName: string
  roomNumber: number
  floor: number
  orders: GuestOrder[]
  maintenanceRequests: GuestMaintenance[]
  cleaningRequests: GuestCleaning[]
  loading: boolean
  error: string | null
}

export const useGuestPortalStore = defineStore('guest-portal', {
  state: (): State => ({
    guestName: '',
    roomNumber: 0,
    floor: 0,
    orders: [],
    maintenanceRequests: [],
    cleaningRequests: [],
    loading: false,
    error: null as string | null
  }),
  actions: {
    async fetchDashboard() {
      this.loading = true
      this.error = null
      try {
        const data: GuestDashboard = await guestPortalApi.dashboard()
        this.guestName = data.guest_name
        this.roomNumber = data.room_number
        this.floor = data.floor
        this.orders = data.orders
        this.maintenanceRequests = data.maintenance_requests
        this.cleaningRequests = data.cleaning_requests
      } catch (e: any) {
        this.error = e?.response?.data?.detail || e?.message || 'Yuklanmadi'
      } finally {
        this.loading = false
      }
    },
    async submitOrder(items: GuestOrderItem[]) {
      const order = await guestPortalApi.createOrder(items)
      this.orders.unshift(order)
      return order
    },
    async submitMaintenance(description: string) {
      const resp = await guestPortalApi.createMaintenance(description)
      // Backend only publishes event, no local persistence — add optimistically
      this.maintenanceRequests.unshift({
        id: crypto.randomUUID(),
        description,
        status: 'reported',
        urgency: 'normal',
        reported_at: new Date().toISOString(),
        assigned_at: null,
        resolved_at: null,
      })
    },
    async submitCleaning(data: { priority: string; preferred_time: string; note?: string }) {
      const cr = await guestPortalApi.createCleaning(data)
      this.cleaningRequests.unshift(cr)
      return cr
    },
    // Called by WS event handler to update order status
    updateOrderStatus(orderId: string, newStatus: string, timestamps: Record<string, string>) {
      const order = this.orders.find((o) => o.id === orderId)
      if (order) {
        order.status = newStatus
        Object.assign(order, timestamps)
      }
    }
  }
})
