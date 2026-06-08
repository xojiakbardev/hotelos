<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import {
  receptionApi,
  type CheckInResponse,
  type CleaningPreference,
  type Guest,
  type Proximity,
  type Room,
  type RoomType
} from '@/api/reception'
import { reservationsApi, type Reservation } from '@/api/reservations'
import { useToastStore } from '@/stores/toast'
import { parseApiError } from '@/composables/useOptimistic'
import { Loader2, Copy, Check as CheckIcon, CalendarCheck, Sparkles } from 'lucide-vue-next'

const props = defineProps<{ room?: Room | null }>()
const emit = defineEmits<{ success: [guest: Guest]; cancel: [] }>()

const toast = useToastStore()

const TYPE_UZ: Record<string, string> = {
  single: 'Bir kishilik',
  double: 'Ikki kishilik',
  suite: 'Lyuks',
  accessible: 'Nogironlar uchun'
}

const isDirect = computed(() => !!props.room)

const form = ref({
  full_name: '',
  phone: '',
  passport_number: '',
  room_type: (props.room?.room_type ?? 'double') as RoomType,
  nights: 1,
  floor_preference: 'none' as 'none' | '1' | '2',
  proximity_preference: 'none' as 'none' | Proximity,
  cleaning_preference: 'afternoon' as CleaningPreference,
  cleaning_preference_note: ''
})

const submitting = ref(false)
const error = ref<string | null>(null)
const successResult = ref<CheckInResponse | null>(null)
const copied = ref(false)

// Reservation lookup — confirmed bookings, picked at the top of the form.
// If picked, we delegate to reservationsApi.checkIn so room/dates are
// honoured (no walk-in matching, no room swap, no re-quoting).
const reservations = ref<Reservation[]>([])
const selectedReservationId = ref<string>('')

onMounted(async () => {
  try { reservations.value = await reservationsApi.list('confirmed') }
  catch { /* ignore */ }
})

watch(selectedReservationId, (id) => {
  if (!id || id === '__none') { selectedReservationId.value = ''; return }
  const r = reservations.value.find((x) => x.id === id)
  if (!r) return
  form.value.full_name = r.full_name
  form.value.phone = r.phone
  form.value.passport_number = r.passport_number || ''
  // Nights derived from reservation date range so the dialog can still show it.
  const inDate = new Date(r.check_in_date)
  const outDate = new Date(r.check_out_date)
  const ms = Math.max(0, outDate.getTime() - inDate.getTime())
  form.value.nights = Math.max(1, Math.round(ms / 86_400_000))
})

function clearReservation() {
  selectedReservationId.value = ''
}

// Returning-guest lookup: if the phone matches a past guest, pull their
// name from history so reception doesn't retype it. Debounced to avoid
// hitting the API on every keystroke.
const PHONE_REGEX = /^\+?[1-9]\d{9,14}$/
const lookupHistory = ref<{ full_name: string; total_stays: number; repeat_visitor: boolean } | null>(null)
const lookingUp = ref(false)
let lookupTimer: ReturnType<typeof setTimeout> | null = null

watch(() => form.value.phone, (phone) => {
  lookupHistory.value = null
  if (lookupTimer) clearTimeout(lookupTimer)
  // Skip if reservation already filled the form, or phone is invalid.
  if (selectedReservationId.value) return
  const cleaned = phone.trim()
  if (!PHONE_REGEX.test(cleaned)) return
  lookupTimer = setTimeout(async () => {
    lookingUp.value = true
    try {
      const h = await receptionApi.guestHistory(cleaned)
      if (h && h.total_stays > 0) {
        lookupHistory.value = { full_name: h.full_name, total_stays: h.total_stays, repeat_visitor: h.repeat_visitor }
        // Only auto-fill name if the field is empty — never overwrite
        // what the user has already typed.
        if (!form.value.full_name.trim()) form.value.full_name = h.full_name
      }
    } catch { /* no prior stays — silent */ }
    finally { lookingUp.value = false }
  }, 400)
})

function money(minor: number) { return (minor / 100).toLocaleString('uz-UZ') + " so'm" }

function copyCredentials() {
  if (!successResult.value) return
  const text = `Login: ${successResult.value.guest_login}\nPIN: ${successResult.value.guest_pin}`
  navigator.clipboard.writeText(text)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

async function submit() {
  error.value = null
  submitting.value = true
  try {
    const noteValue = form.value.cleaning_preference_note.trim() || undefined
    let result: CheckInResponse
    if (selectedReservationId.value) {
      const r = await reservationsApi.checkIn(selectedReservationId.value)
      result = {
        ...r,
        phone: form.value.phone.trim(),
        floor: 0,
      } as unknown as CheckInResponse
    } else {
      result = await receptionApi.checkIn(
        isDirect.value
          ? {
              full_name: form.value.full_name.trim(),
              phone: form.value.phone.trim(),
              passport_number: form.value.passport_number.trim() || undefined,
              nights: form.value.nights,
              room_id: props.room!.id,
              cleaning_preference: form.value.cleaning_preference,
              cleaning_preference_note: noteValue
            }
          : {
              full_name: form.value.full_name.trim(),
              phone: form.value.phone.trim(),
              passport_number: form.value.passport_number.trim() || undefined,
              room_type: form.value.room_type,
              nights: form.value.nights,
              floor_preference: form.value.floor_preference !== 'none' ? Number(form.value.floor_preference) : undefined,
              proximity_preference: form.value.proximity_preference !== 'none' ? form.value.proximity_preference : undefined,
              cleaning_preference: form.value.cleaning_preference,
              cleaning_preference_note: noteValue
            }
      )
    }
    toast.success(`#${result.room_number}-xona ${result.full_name} ga tayinlandi`)
    successResult.value = result
  } catch (e: unknown) {
    const err = e as { response?: { data?: { error?: string; room_type?: string; message?: string } } }
    const data = err.response?.data
    if (data?.error === 'no_rooms_available') {
      error.value = "So'ralgan turdagi toza xona hozirda mavjud emas."
    } else if (data?.error === 'room_not_available') {
      error.value = "Bu xona endi bo'sh emas — boshqa kimdir band qildi yoki tozalanmoqda."
    } else {
      error.value = parseApiError(e)
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <!-- Success state — show credentials -->
  <div v-if="successResult" class="space-y-5">
    <div class="rounded-lg bg-success/10 border border-success/20 p-4 text-center space-y-2">
      <p class="text-green-700 font-semibold">Mehmon muvaffaqiyatli qabul qilindi!</p>
      <p class="text-sm text-muted-foreground">#{{ successResult.room_number }}-xona · {{ successResult.full_name }}</p>
    </div>

    <div class="rounded-lg border p-4 space-y-3">
      <p class="text-sm font-semibold">Mehmon kirish ma'lumotlari</p>
      <div class="grid grid-cols-2 gap-3">
        <div class="space-y-1">
          <p class="text-xs text-muted-foreground">Login (telefon)</p>
          <p class="font-mono font-semibold">{{ successResult.guest_login }}</p>
        </div>
        <div class="space-y-1">
          <p class="text-xs text-muted-foreground">PIN kod</p>
          <p class="font-mono font-bold text-xl text-primary tracking-widest">{{ successResult.guest_pin }}</p>
        </div>
      </div>
      <Button variant="outline" size="sm" class="w-full" @click="copyCredentials">
        <component :is="copied ? CheckIcon : Copy" class="w-4 h-4 mr-2" />
        {{ copied ? 'Nusxalandi!' : 'Nusxalash' }}
      </Button>
      <p class="text-xs text-muted-foreground text-center">Bu PIN mehmon portaliga kirish uchun. Mehmonning telefoni login bo'ladi.</p>
    </div>

    <div class="flex justify-end">
      <Button @click="emit('success', successResult)">Yopish</Button>
    </div>
  </div>

  <!-- Form -->
  <form v-else @submit.prevent="submit" class="space-y-5" novalidate>
    <!-- Reservation lookup (only when not direct-room) -->
    <div v-if="!isDirect && reservations.length" class="space-y-2">
      <Label class="flex items-center gap-1.5">
        <CalendarCheck class="w-3.5 h-3.5" />
        Mavjud bron (ixtiyoriy)
      </Label>
      <Select v-model="selectedReservationId">
        <SelectTrigger><SelectValue placeholder="Walk-in (bronsiz) — yoki bron tanlang" /></SelectTrigger>
        <SelectContent>
          <SelectItem value="__none">Walk-in (bronsiz)</SelectItem>
          <SelectItem v-for="r in reservations" :key="r.id" :value="r.id">
            #{{ r.room_number }} · {{ r.full_name }} · {{ r.phone }}
          </SelectItem>
        </SelectContent>
      </Select>
      <p v-if="selectedReservationId" class="text-[11px] text-muted-foreground">
        Bron tanlandi — mehmon ma'lumotlari avtomatik to'ldirildi.
        <button type="button" class="text-primary hover:underline" @click="clearReservation">Bekor qilish</button>
      </p>
    </div>

    <!-- Direct room banner -->
    <div v-if="isDirect && room" class="rounded-lg bg-primary/5 border border-primary/20 p-4 flex items-center gap-4">
      <div>
        <p class="text-xl font-bold text-primary">#{{ room.room_number }}</p>
        <p class="text-xs text-muted-foreground">{{ room.floor }}-qavat</p>
      </div>
      <div class="flex items-center gap-2 text-sm">
        <Badge variant="secondary">{{ TYPE_UZ[room.room_type] || room.room_type }}</Badge>
        <span class="tabular-nums">{{ money(room.nightly_rate_minor_units) }} / tun</span>
      </div>
    </div>

    <!-- Guest info -->
    <fieldset class="space-y-3">
      <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Mehmon</p>
      <div class="grid grid-cols-2 gap-3">
        <div class="space-y-1.5">
          <Label>To'liq ism</Label>
          <Input v-model="form.full_name" required />
        </div>
        <div class="space-y-1.5">
          <Label class="flex items-center gap-1.5">
            Telefon
            <Loader2 v-if="lookingUp" class="w-3 h-3 animate-spin text-muted-foreground" />
          </Label>
          <Input v-model="form.phone" type="tel" placeholder="+998901234567" required />
        </div>
      </div>
      <div v-if="lookupHistory" class="flex items-center gap-2 text-xs text-primary bg-primary/5 border border-primary/15 rounded-md px-3 py-2">
        <Sparkles class="w-3.5 h-3.5 shrink-0" />
        <span>
          <strong>{{ lookupHistory.full_name }}</strong> — {{ lookupHistory.total_stays }} marta yashagan{{ lookupHistory.repeat_visitor ? ' (doimiy)' : '' }}. Ism avtomatik to'ldirildi.
        </span>
      </div>
      <div class="space-y-1.5">
        <Label>Pasport (ixtiyoriy)</Label>
        <Input v-model="form.passport_number" />
      </div>
    </fieldset>

    <!-- Stay -->
    <fieldset class="space-y-3">
      <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Qolish</p>
      <div class="grid grid-cols-2 gap-3">
        <div v-if="!isDirect" class="space-y-1.5">
          <Label>Xona turi</Label>
          <Select v-model="form.room_type">
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="single">Bir kishilik</SelectItem>
              <SelectItem value="double">Ikki kishilik</SelectItem>
              <SelectItem value="suite">Lyuks</SelectItem>
              <SelectItem value="accessible">Nogironlar uchun</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label>Tunlar soni</Label>
          <Input v-model.number="form.nights" type="number" min="1" max="365" required />
        </div>
      </div>
    </fieldset>

    <!-- Cleaning preference -->
    <fieldset class="space-y-3">
      <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Tozalash afzalligi</p>
      <div class="grid grid-cols-2 gap-3">
        <div class="space-y-1.5">
          <Label>Vaqt</Label>
          <Select v-model="form.cleaning_preference">
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="morning">Ertalab</SelectItem>
              <SelectItem value="afternoon">Tushdan keyin</SelectItem>
              <SelectItem value="evening">Kechqurun</SelectItem>
              <SelectItem value="custom">Maxsus</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div v-if="form.cleaning_preference === 'custom'" class="space-y-1.5">
          <Label>Izoh</Label>
          <Input v-model="form.cleaning_preference_note" placeholder="masalan: 10:30" />
        </div>
      </div>
    </fieldset>

    <!-- Preferences (algorithm mode) -->
    <fieldset v-if="!isDirect" class="space-y-3">
      <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Afzalliklar (ixtiyoriy)</p>
      <div class="grid grid-cols-2 gap-3">
        <div class="space-y-1.5">
          <Label>Qavat</Label>
          <Select v-model="form.floor_preference">
            <SelectTrigger><SelectValue placeholder="Afzallik yo'q" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="none">Afzallik yo'q</SelectItem>
              <SelectItem value="1">1-qavat</SelectItem>
              <SelectItem value="2">2-qavat</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label>Joylashuv</Label>
          <Select v-model="form.proximity_preference">
            <SelectTrigger><SelectValue placeholder="Afzallik yo'q" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="none">Afzallik yo'q</SelectItem>
              <SelectItem value="elevator">Lift yonida</SelectItem>
              <SelectItem value="stairs">Zinapoya yonida</SelectItem>
              <SelectItem value="other">Boshqa</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </fieldset>

    <div v-if="error" class="rounded-md bg-destructive/10 text-destructive text-sm p-3" role="alert">
      {{ error }}
    </div>

    <div class="flex justify-end gap-2 pt-2">
      <Button variant="outline" type="button" :disabled="submitting" @click="emit('cancel')">Bekor</Button>
      <Button type="submit" :disabled="submitting">
        <Loader2 v-if="submitting" class="w-4 h-4 mr-2 animate-spin" />
        {{ isDirect ? `#${room?.room_number}-xonaga qabul qilish` : 'Qabul qilish' }}
      </Button>
    </div>
  </form>
</template>
