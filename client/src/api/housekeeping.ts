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
  photo_path: string | null
}

export const housekeepingApi = {
  listQueue: () => api.get<CleaningEntry[]>('/housekeeping/queue').then((r) => r.data),
  listHistory: () => api.get<CleaningEntry[]>('/housekeeping/queue/history').then((r) => r.data),
  start: (entryId: string) =>
    api.post<CleaningEntry>(`/housekeeping/queue/${entryId}/start`).then((r) => r.data),
  complete: (entryId: string, photo?: File | null) => {
    if (photo) {
      const form = new FormData()
      form.append('photo', photo)
      return api
        .post<CleaningEntry>(`/housekeeping/queue/${entryId}/complete`, form, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        .then((r) => r.data)
    }
    return api
      .post<CleaningEntry>(`/housekeeping/queue/${entryId}/complete`)
      .then((r) => r.data)
  },
  getSettings: () =>
    api.get<{ photo_required: boolean }>('/housekeeping/queue/settings').then((r) => r.data),
  updateSettings: (photoRequired: boolean) =>
    api
      .put<{ photo_required: boolean }>('/housekeeping/queue/settings', {
        photo_required: photoRequired
      })
      .then((r) => r.data),
  fetchPhoto: (path: string) =>
    api
      .get(`/housekeeping/queue/photos/${path}`, { responseType: 'blob' })
      .then((r) => URL.createObjectURL(r.data as Blob))
}
