import { api } from './client'

export type Role = 'manager' | 'reception' | 'technician' | 'cleaner' | 'kitchen' | 'guest'

export interface TokenResponse {
  access_token: string
  token_type: string
  role: Role
  user_id: string
  phone: string
  full_name: string | null
  guest_id: string | null
  room_id: string | null
  room_number: number | null
  must_change_password: boolean
}

export interface MeResponse {
  id: string
  phone: string
  full_name: string | null
  role: Role
  is_active: boolean
  must_change_password: boolean
  guest_id?: string | null
  room_id?: string | null
  room_number?: number | null
}

export interface UserOut {
  id: string
  phone: string
  full_name: string | null
  role: Role
  is_active: boolean
}

export interface UserCreate {
  phone: string
  password: string
  role: Role
  full_name?: string
}

export interface UserUpdate {
  full_name?: string | null
  role?: Role
  password?: string
  is_active?: boolean
}

export const authApi = {
  login: (phone: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { phone, password }).then((r) => r.data),
  me: () => api.get<MeResponse>('/auth/me').then((r) => r.data),
  changePassword: (currentPassword: string, newPassword: string) =>
    api
      .post<TokenResponse>('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      })
      .then((r) => r.data),
  listUsers: (role?: Role) =>
    api
      .get<UserOut[]>('/auth/users', { params: role ? { role } : undefined })
      .then((r) => r.data),
  createUser: (payload: UserCreate) =>
    api.post<UserOut>('/auth/users', payload).then((r) => r.data),
  updateUser: (id: string, payload: UserUpdate) =>
    api.put<UserOut>(`/auth/users/${id}`, payload).then((r) => r.data),
  deleteUser: (id: string) =>
    api.delete(`/auth/users/${id}`).then(() => undefined)
}
