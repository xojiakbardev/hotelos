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
  cleaningPreference: string
  cleaningPreferenceNote: string
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
    cleaningPreference: 'afternoon',
    cleaningPreferenceNote: '',
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
        this.cleaningPreference = data.cleaning_preference || 'afternoon'
        this.cleaningPreferenceNote = data.cleaning_preference_note || ''
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
      await guestPortalApi.createMaintenance(description)
      // Don't add an optimistic record — the maintenance-service handler
      // creates the real Issue and the projection row arrives via the
      // maintenance.reported WS event, which triggers fetchDashboard().
      // Adding an optimistic row here just causes a brief duplicate flash.
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
