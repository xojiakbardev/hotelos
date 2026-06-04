import { api } from './client'

export type Urgency = 'critical' | 'high' | 'normal' | 'low'
export type IssueStatus = 'reported' | 'assigned' | 'resolved'

export interface Issue {
  id: string
  room_id: string
  room_number: number
  floor: number
  urgency: Urgency
  description: string
  status: IssueStatus
  reported_by_user_id: string
  reported_at: string
  assigned_technician_id: string | null
  assigned_at: string | null
  resolved_at: string | null
  resolved_by_user_id: string | null
}

export interface IssueReport {
  room_id: string
  room_number: number
  floor: number
  urgency: Urgency
  description: string
}

export const maintenanceApi = {
  queue: () => api.get<Issue[]>('/maintenance/queue').then((r) => r.data),
  myQueue: () => api.get<Issue[]>('/maintenance/my').then((r) => r.data),
  history: () => api.get<Issue[]>('/maintenance/history').then((r) => r.data),
  report: (payload: IssueReport) =>
    api.post<Issue>('/maintenance/issues', payload).then((r) => r.data),
  claim: (issueId: string) =>
    api.post<Issue>(`/maintenance/issues/${issueId}/assign-me`).then((r) => r.data),
  resolve: (issueId: string) =>
    api.post<Issue>(`/maintenance/issues/${issueId}/resolve`).then((r) => r.data)
}
