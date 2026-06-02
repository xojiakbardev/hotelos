<script setup lang="ts">
/**
 * Colour-coded status pill.
 *
 * Pass `tone` (the raw status string from the API). The component:
 *   * picks a colour from `toneToVar`
 *   * picks an Uzbek label from `toneLabels` (so the UI never shows raw
 *     English status strings like "occupied")
 *
 * A caller can override the displayed text with `label` — useful for roles
 * and other domain-specific names that don't share the status namespace.
 */
const props = withDefaults(
  defineProps<{ tone: string; label?: string }>(),
  { label: undefined }
)

const toneToVar: Record<string, string> = {
  // Rooms
  clean: 'var(--status-clean)',
  dirty: 'var(--status-dirty)',
  cleaning: 'var(--status-cleaning)',
  maintenance: 'var(--status-maintenance)',
  occupied: 'var(--status-occupied)',
  available: 'var(--status-clean)',
  out_of_service: 'var(--status-maintenance)',
  // Housekeeping queue
  pending: 'var(--status-dirty)',
  in_progress: 'var(--status-cleaning)',
  completed: 'var(--status-clean)',
  // Maintenance issues
  reported: 'var(--status-maintenance)',
  assigned: 'var(--status-cleaning)',
  resolved: 'var(--status-clean)',
  critical: 'var(--status-maintenance)',
  high: 'var(--status-dirty)',
  normal: 'var(--status-cleaning)',
  low: 'var(--ink-500)',
  // Room-service order lifecycle
  received: 'var(--status-dirty)',
  preparing: 'var(--status-cleaning)',
  delivering: 'var(--primary)',
  delivered: 'var(--status-clean)'
}

const toneLabels: Record<string, string> = {
  // Rooms
  clean: 'Toza',
  dirty: 'Iflos',
  cleaning: 'Tozalanmoqda',
  maintenance: 'Texnik xizmatda',
  occupied: 'Band',
  available: 'Bo‘sh',
  out_of_service: 'Xizmatdan tashqari',
  // Housekeeping queue
  pending: 'Kutmoqda',
  in_progress: 'Bajarilmoqda',
  completed: 'Tugatildi',
  // Maintenance issues
  reported: 'Qayd etildi',
  assigned: 'Tayinlandi',
  resolved: 'Hal qilindi',
  critical: 'Kritik',
  high: 'Yuqori',
  normal: 'O‘rta',
  low: 'Past',
  // Room-service order lifecycle
  received: 'Qabul qilindi',
  preparing: 'Tayyorlanmoqda',
  delivering: 'Yetkazilmoqda',
  delivered: 'Yetkazildi'
}
</script>

<template>
  <span
    class="badge"
    :style="{ '--badge-color': toneToVar[props.tone] ?? 'var(--ink-500)' }"
  >
    <span class="badge-dot" aria-hidden="true" />
    {{ props.label ?? toneLabels[props.tone] ?? props.tone }}
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: 600;
  background: color-mix(in srgb, var(--badge-color) 12%, transparent);
  color: var(--badge-color);
  white-space: nowrap;
  letter-spacing: 0.01em;
}
.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--badge-color);
}
</style>
