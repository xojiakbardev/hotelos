/**
 * Uzbek labels for status strings shared across views.
 *
 * Use these in toast messages, banners, and anywhere else status text
 * is shown OUTSIDE a <StatusBadge>. (StatusBadge already maps internally.)
 */

export const ROOM_STATUS_UZ: Record<string, string> = {
  available: 'bo‘sh',
  occupied: 'band',
  out_of_service: 'xizmatdan tashqari'
}

export const CLEANLINESS_UZ: Record<string, string> = {
  clean: 'toza',
  dirty: 'iflos',
  cleaning: 'tozalanmoqda',
  maintenance: 'texnik xizmatda'
}

export const ROOM_TYPE_UZ: Record<string, string> = {
  single: 'Bir kishilik',
  double: 'Ikki kishilik',
  suite: 'Lyuks',
  accessible: 'Nogironlar uchun'
}

export const PROXIMITY_UZ: Record<string, string> = {
  elevator: 'Lift yonida',
  stairs: 'Zinapoya yonida'
}

export const CLEANING_STATUS_UZ: Record<string, string> = {
  pending: 'kutmoqda',
  in_progress: 'bajarilmoqda',
  completed: 'tugatildi'
}

export const ISSUE_STATUS_UZ: Record<string, string> = {
  reported: 'qayd etildi',
  assigned: 'tayinlandi',
  resolved: 'hal qilindi'
}

export const URGENCY_UZ: Record<string, string> = {
  critical: 'Kritik',
  high: 'Yuqori',
  normal: 'O‘rta',
  low: 'Past'
}

export const ORDER_STATUS_UZ: Record<string, string> = {
  received: 'qabul qilindi',
  preparing: 'tayyorlanmoqda',
  delivering: 'yetkazilmoqda',
  delivered: 'yetkazildi'
}

export const ROLE_UZ: Record<string, string> = {
  manager: 'Boshqaruvchi',
  reception: 'Qabulchi',
  technician: 'Texnik',
  cleaner: 'Tozalovchi'
}

/**
 * Broker channel / event names. These appear on the dashboard's live
 * event stream — we localise them so the manager doesn't see raw
 * `guests.checked_in` strings.
 */
export const EVENT_UZ: Record<string, string> = {
  'guests.checked_in':              'Mehmon qabul qilindi',
  'guests.checked_out':             'Mehmon jo‘natildi',
  'bills.finalized':                'Hisob yakunlandi',
  'rooms.vacated':                  'Xona bo‘shadi',
  'rooms.added_to_cleaning_queue':  'Tozalash navbatiga qo‘shildi',
  'rooms.cleaning_started':         'Tozalash boshlandi',
  'rooms.cleaned':                  'Xona tozalandi',
  'orders.received':                'Buyurtma qabul qilindi',
  'orders.preparing':               'Buyurtma tayyorlanmoqda',
  'orders.delivering':              'Buyurtma yetkazilmoqda',
  'orders.delivered':               'Buyurtma yetkazildi',
  'maintenance.reported':           'Muammo qayd etildi',
  'maintenance.assigned':           'Texnikka tayinlandi',
  'maintenance.resolved':           'Muammo hal qilindi'
}

/** Generic helper — returns the Uzbek label for a status string from any
 *  of the maps above, falling back to the raw value. */
export function uzStatus(value: string): string {
  return (
    ROOM_STATUS_UZ[value] ??
    CLEANLINESS_UZ[value] ??
    CLEANING_STATUS_UZ[value] ??
    ISSUE_STATUS_UZ[value] ??
    ORDER_STATUS_UZ[value] ??
    URGENCY_UZ[value] ??
    value
  )
}
