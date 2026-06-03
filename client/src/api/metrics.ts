import { api } from './client'

export interface DashboardMetrics {
  rooms_total: number
  rooms_occupied: number
  rooms_available_clean: number
  occupancy_rate: number
  active_guests: number
  open_orders: number
  revenue_today_minor_units: number
  revenue_week_minor_units: number
}

export const metricsApi = {
  dashboard: () =>
    api.get<DashboardMetrics>('/reception/metrics/dashboard').then((r) => r.data)
}
