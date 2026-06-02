import { api } from './client'

export type Role = 'manager' | 'reception' | 'technician' | 'cleaner'

export interface TokenResponse {
  access_token: string
  token_type: string
  role: Role
  user_id: string
  phone: string
  full_name: string | null
}

export interface MeResponse {
  id: string
  phone: string
  full_name: string | null
  role: Role
  is_active: boolean
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

export const authApi = {
  login: (phone: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { phone, password }).then((r) => r.data),
  me: () => api.get<MeResponse>('/auth/me').then((r) => r.data),
  listUsers: (role?: Role) =>
    api
      .get<UserOut[]>('/auth/users', { params: role ? { role } : undefined })
      .then((r) => r.data),
  createUser: (payload: UserCreate) =>
    api.post<UserOut>('/auth/users', payload).then((r) => r.data)
}
