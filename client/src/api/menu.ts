import { api } from './client'

export interface MenuItem {
  id: string
  name: string
  category: string
  price_minor_units: number
  prep_minutes: number
  is_available: boolean
  created_at: string
  updated_at: string
}

export interface MenuItemPayload {
  name: string
  category: string
  price_minor_units: number
  prep_minutes: number
  is_available: boolean
}

export const menuApi = {
  list: (availableOnly = false) =>
    api
      .get<MenuItem[]>('/room-service/menu', {
        params: availableOnly ? { available_only: true } : undefined
      })
      .then((r) => r.data),
  create: (payload: MenuItemPayload) =>
    api.post<MenuItem>('/room-service/menu', payload).then((r) => r.data),
  update: (id: string, payload: Partial<MenuItemPayload>) =>
    api.put<MenuItem>(`/room-service/menu/${id}`, payload).then((r) => r.data),
  setAvailability: (id: string, isAvailable: boolean) =>
    api
      .patch<MenuItem>(`/room-service/menu/${id}/availability`, { is_available: isAvailable })
      .then((r) => r.data),
  remove: (id: string) => api.delete(`/room-service/menu/${id}`).then(() => undefined)
}
