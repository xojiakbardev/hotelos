import { api } from './client'

export type ReservationStatus =
  | 'pending'
  | 'confirmed'
  | 'checked_in'
  | 'cancelled'
  | 'no_show'

export interface Reservation {
  id: string
  full_name: string
  phone: string
  passport_number: string | null
  room_id: string
  room_number: number
  floor: number
  check_in_date: string
  check_out_date: string
  status: ReservationStatus
  nightly_rate_locked_minor_units: number
  guest_id: string | null
  status_changed_at: string
  created_at: string
}

export interface ReservationCreatePayload {
  full_name: string
  phone: string
  passport_number?: string
  room_id: string
  check_in_date: string
  check_out_date: string
}

export const reservationsApi = {
  list: (statusFilter?: ReservationStatus) =>
    api
      .get<Reservation[]>('/reception/reservations', {
        params: statusFilter ? { status_filter: statusFilter } : undefined
      })
      .then((r) => r.data),
  create: (payload: ReservationCreatePayload) =>
    api.post<Reservation>('/reception/reservations', payload).then((r) => r.data),
  confirm: (id: string) =>
    api.post<Reservation>(`/reception/reservations/${id}/confirm`).then((r) => r.data),
  cancel: (id: string) =>
    api.post<Reservation>(`/reception/reservations/${id}/cancel`).then((r) => r.data),
  noShow: (id: string) =>
    api.post<Reservation>(`/reception/reservations/${id}/no-show`).then((r) => r.data),
  checkIn: (id: string) =>
    api
      .post<{ guest_pin: string; guest_login: string; room_number: number; full_name: string }>(`/reception/reservations/${id}/check-in`, {})
      .then((r) => r.data)
}
