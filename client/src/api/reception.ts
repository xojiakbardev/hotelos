import { api } from './client'

export type RoomType = 'single' | 'double' | 'suite' | 'accessible'
export type Proximity = 'elevator' | 'stairs'
export type Cleanliness = 'clean' | 'dirty' | 'cleaning' | 'maintenance'
export type RoomStatus = 'available' | 'occupied' | 'out_of_service'

export interface Room {
  id: string
  room_number: number
  floor: number
  room_type: RoomType
  proximity: Proximity
  cleanliness_status: Cleanliness
  status: RoomStatus
  nightly_rate_minor_units: number
  last_cleaned_at: string
  last_assigned_at: string | null
}

export type CleaningPreference = 'morning' | 'afternoon' | 'evening' | 'custom'

export interface CheckInPayload {
  full_name: string
  phone: string
  passport_number?: string
  nights: number
  // Either room_id (direct, skip algorithm) or room_type (algorithm picks).
  room_id?: string
  room_type?: RoomType
  floor_preference?: number
  proximity_preference?: Proximity
  cleaning_preference?: CleaningPreference
  cleaning_preference_note?: string
}

export interface Guest {
  id: string
  full_name: string
  phone: string
  room_id: string
  room_number: number
  floor: number
  room_type: RoomType
  checked_in_at: string
  expected_checkout_at: string
  nightly_rate_locked_minor_units: number
  do_not_disturb: boolean
  cleaning_preference: CleaningPreference
  cleaning_preference_note: string | null
}

export interface Bill {
  guest_id: string
  room_number: number
  bill_id: string
  nights: number
  nightly_rate_minor_units: number
  room_cost_minor_units: number
  room_service_charges_minor_units: number
  extras_minor_units: number
  discount_minor_units: number
  total_minor_units: number
  finalized_at: string
  checked_out_at: string
}

export type OrderStatus = 'received' | 'preparing' | 'delivering' | 'delivered'

export interface OrderItem {
  name: string
  qty: number
  price_minor_units: number
}

export interface Order {
  id: string
  guest_id: string
  room_id: string
  room_number: number
  floor: number
  status: OrderStatus
  items: OrderItem[]
  total_minor_units: number
  taken_by_user_id: string
  received_at: string
  preparing_at: string | null
  delivering_at: string | null
  delivered_at: string | null
}

export interface OrderCreate {
  guest_id: string
  items: OrderItem[]
}

export interface DailyCount {
  date: string
  count: number
}

export interface StaySummary {
  guest_id: string
  room_number: number
  floor: number
  checked_in_at: string
  checked_out_at: string | null
  nights: number
  total_minor_units: number | null
  bill_id: string | null
}

export interface GuestHistory {
  phone: string
  full_name: string
  stays: StaySummary[]
  total_stays: number
  total_nights: number
  total_spent_minor_units: number
  last_checked_in_at: string | null
  repeat_visitor: boolean
}

export interface RoomCreatePayload {
  room_number: number
  floor: number
  room_type: RoomType
  proximity: Proximity
  nightly_rate_minor_units: number
}

export type RoomUpdatePayload = Partial<{
  floor: number
  room_type: RoomType
  proximity: Proximity
  nightly_rate_minor_units: number
}>

export const receptionApi = {
  listRooms: () => api.get<{ rooms: Room[]; total: number }>('/reception/rooms').then((r) => r.data),
  createRoom: (payload: RoomCreatePayload) =>
    api.post<Room>('/reception/rooms', payload).then((r) => r.data),
  updateRoom: (id: string, payload: RoomUpdatePayload) =>
    api.put<Room>(`/reception/rooms/${id}`, payload).then((r) => r.data),
  deleteRoom: (id: string) => api.delete(`/reception/rooms/${id}`).then(() => undefined),
  listGuests: () => api.get<Guest[]>('/reception/guests').then((r) => r.data),
  dailyGuestStats: (days = 30) =>
    api
      .get<DailyCount[]>('/reception/guests/stats/daily', { params: { days } })
      .then((r) => r.data),
  checkIn: (payload: CheckInPayload) =>
    api.post<Guest>('/reception/guests/check-in', payload).then((r) => r.data),
  checkOut: (guestId: string) =>
    api.post<Bill>(`/reception/guests/${guestId}/check-out`).then((r) => r.data),
  getGuest: (id: string) => api.get<Guest>(`/reception/guests/${id}`).then((r) => r.data),
  guestHistory: (phone: string) =>
    api
      .get<GuestHistory>(`/reception/guests/history/by-phone/${encodeURIComponent(phone)}`)
      .then((r) => r.data),
  setDnd: (guestId: string, value: boolean) =>
    api
      .put<Guest>(`/reception/guests/${guestId}/dnd`, { do_not_disturb: value })
      .then((r) => r.data),
  setCleaningPreference: (
    guestId: string,
    preference: CleaningPreference,
    note?: string | null
  ) =>
    api
      .put<Guest>(`/reception/guests/${guestId}/cleaning-preference`, {
        cleaning_preference: preference,
        cleaning_preference_note: note ?? null
      })
      .then((r) => r.data),
  listOrders: () => api.get<Order[]>('/reception/orders').then((r) => r.data),
  createOrder: (payload: OrderCreate) =>
    api.post<Order>('/reception/orders', payload).then((r) => r.data),
  advanceOrder: (orderId: string) =>
    api.post<Order>(`/reception/orders/${orderId}/advance`).then((r) => r.data)
}
