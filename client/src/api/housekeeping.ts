import { api } from './client'

export type CleaningStatus = 'pending' | 'in_progress' | 'completed'

export type CleaningPreference = 'morning' | 'afternoon' | 'evening' | 'custom'

export interface CleaningEntry {
  id: string
  room_id: string
  room_number: number
  floor: number
  status: CleaningStatus
  queued_at: string
  started_at: string | null
  completed_at: string | null
  assigned_cleaner_id: string | null
  do_not_disturb: boolean
  cleaning_preference: CleaningPreference
  cleaning_preference_note: string | null
}

export const housekeepingApi = {
  listQueue: () => api.get<CleaningEntry[]>('/housekeeping/queue').then((r) => r.data),
  start: (entryId: string) =>
    api.post<CleaningEntry>(`/housekeeping/queue/${entryId}/start`).then((r) => r.data),
  complete: (entryId: string) =>
    api.post<CleaningEntry>(`/housekeeping/queue/${entryId}/complete`).then((r) => r.data)
}
