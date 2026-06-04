import { api } from './client'

export interface GuestOrderItem {
  menu_item_id?: string
  name: string
  qty: number
  price_minor_units: number
}

export interface MenuItem {
  id: string
  name: string
  category: string
  price_minor_units: number
  prep_minutes: number
  is_available: boolean
}

export interface GuestOrder {
  id: string
  status: string
  items: GuestOrderItem[]
  total_minor_units: number
  received_at: string
  preparing_at: string | null
  delivering_at: string | null
  delivered_at: string | null
}

export interface GuestMaintenance {
  id: string
  description: string
  status: string
  urgency: string
  reported_at: string
  assigned_at: string | null
  resolved_at: string | null
}

export interface GuestCleaning {
  id: string
  priority: string
  preferred_time: string
  note: string | null
  status: string
  requested_at: string
  completed_at: string | null
}

export interface GuestDashboard {
  guest_name: string
  room_number: number
  floor: number
  orders: GuestOrder[]
  maintenance_requests: GuestMaintenance[]
  cleaning_requests: GuestCleaning[]
}

export const guestPortalApi = {
  dashboard: () =>
    api.get<GuestDashboard>('/reception/guest-portal/dashboard').then((r) => r.data),

  menu: () =>
    api.get<MenuItem[]>('/room-service/menu', { params: { available_only: true } }).then((r) => r.data),

  createOrder: (items: GuestOrderItem[]) =>
    api.post<GuestOrder>('/reception/guest-portal/orders', { items }).then((r) => r.data),

  createMaintenance: (description: string) =>
    api
      .post('/reception/guest-portal/maintenance', { description })
      .then((r) => r.data),

  createCleaning: (data: { priority: string; preferred_time: string; note?: string }) =>
    api
      .post<GuestCleaning>('/reception/guest-portal/cleaning', data)
      .then((r) => r.data),
}
