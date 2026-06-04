<script setup lang="ts">
import { ref, watch } from 'vue'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { receptionApi, type Room, type Guest } from '@/api/reception'
import { ROOM_TYPE_UZ } from '@/lib/labels'

const props = defineProps<{ room: Room | null; open: boolean }>()
const emit = defineEmits<{ close: [] }>()

const currentGuest = ref<Guest | null>(null)
const loading = ref(false)

// Keep last room data visible during close animation
const displayRoom = ref<Room | null>(null)
watch(() => props.room, (r) => { if (r) displayRoom.value = r })
watch(() => props.open, (v) => { if (v && props.room) loadData() })

async function loadData() {
  if (!props.room) return
  loading.value = true
  try {
    const guests = await receptionApi.listGuests().catch(() => [])
    currentGuest.value = guests.find(g => g.room_id === props.room!.id) || null
  } finally { loading.value = false }
}

const CLEAN_UZ: Record<string, string> = { clean: 'Toza', dirty: 'Iflos', cleaning: 'Tozalanmoqda', maintenance: "Ta'mirda" }
const STATUS_UZ: Record<string, string> = { available: "Bo'sh", occupied: 'Band', out_of_service: 'Xizmatdan chiqarilgan' }
const PROX_UZ: Record<string, string> = { elevator: 'Lift yonida', stairs: 'Zinapoya yonida' }

function money(minor: number) { return (minor / 100).toLocaleString('uz-UZ') + " so'm" }

function statusVariant(s: string): 'success' | 'default' | 'destructive' | 'warning' | 'secondary' {
  if (s === 'available' || s === 'clean') return 'success'
  if (s === 'occupied') return 'default'
  if (s === 'maintenance' || s === 'out_of_service') return 'destructive'
  if (s === 'dirty' || s === 'cleaning') return 'warning'
  return 'secondary'
}
</script>

<template>
  <Dialog :open="open" @update:open="(v: boolean) => { if (!v) emit('close') }">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ displayRoom ? `#${displayRoom.room_number}-xona` : '' }}</DialogTitle>
      </DialogHeader>

      <div v-if="displayRoom" class="space-y-4">
        <div class="flex gap-2">
          <Badge :variant="statusVariant(displayRoom.status)">{{ STATUS_UZ[displayRoom.status] || displayRoom.status }}</Badge>
          <Badge :variant="statusVariant(displayRoom.cleanliness_status)">{{ CLEAN_UZ[displayRoom.cleanliness_status] || displayRoom.cleanliness_status }}</Badge>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div><p class="text-xs uppercase text-muted-foreground font-semibold">Qavat</p><p class="text-sm">{{ displayRoom.floor }}-qavat</p></div>
          <div><p class="text-xs uppercase text-muted-foreground font-semibold">Turi</p><p class="text-sm">{{ ROOM_TYPE_UZ[displayRoom.room_type] || displayRoom.room_type }}</p></div>
          <div><p class="text-xs uppercase text-muted-foreground font-semibold">Joylashuv</p><p class="text-sm">{{ PROX_UZ[displayRoom.proximity] || displayRoom.proximity }}</p></div>
          <div><p class="text-xs uppercase text-muted-foreground font-semibold">Tunlik narx</p><p class="text-sm font-semibold text-primary">{{ money(displayRoom.nightly_rate_minor_units) }}</p></div>
          <div><p class="text-xs uppercase text-muted-foreground font-semibold">Dinamik narx</p><p class="text-sm font-semibold text-primary">{{ money(displayRoom.dynamic_price_minor_units || displayRoom.nightly_rate_minor_units) }}</p></div>
          <div><p class="text-xs uppercase text-muted-foreground font-semibold">Freshness</p><p class="text-sm">{{ Math.round((displayRoom.freshness_score || 0) * 100) }}%</p></div>
          <div><p class="text-xs uppercase text-muted-foreground font-semibold">Oxirgi tozalash</p><p class="text-sm">{{ new Date(displayRoom.last_cleaned_at).toLocaleString('uz-UZ') }}</p></div>
          <div><p class="text-xs uppercase text-muted-foreground font-semibold">Oxirgi tayinlash</p><p class="text-sm">{{ displayRoom.last_assigned_at ? new Date(displayRoom.last_assigned_at).toLocaleString('uz-UZ') : 'Hali yo\'q' }}</p></div>
        </div>

        <Separator />

        <div v-if="currentGuest" class="space-y-2">
          <p class="text-xs font-semibold uppercase text-muted-foreground">Hozirgi mehmon</p>
          <div class="flex items-center gap-3 border rounded-lg p-3">
            <Avatar class="h-8 w-8">
              <AvatarFallback class="text-xs bg-primary/10 text-primary">{{ currentGuest.full_name.slice(0, 1).toUpperCase() }}</AvatarFallback>
            </Avatar>
            <div>
              <p class="text-sm font-medium">{{ currentGuest.full_name }}</p>
              <p class="text-xs text-muted-foreground font-mono">{{ currentGuest.phone }}</p>
            </div>
          </div>
        </div>
        <div v-else-if="displayRoom.status === 'available'" class="text-center py-4 text-sm text-muted-foreground bg-muted/50 rounded-lg">
          Bu xona hozir bo'sh
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
