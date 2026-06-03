<script setup lang="ts">
/**
 * Embeddable check-in form. Mounted inside a Modal from RoomsList/GuestsList.
 *
 * Two modes:
 *   * Default — receptionist picks room type + preferences; the server
 *     runs the assignment algorithm.
 *   * Direct — caller passes a specific `room` prop (e.g. user clicked a
 *     specific available room card). Room type / floor / proximity inputs
 *     are hidden; the picked room is shown in a banner.
 *
 * Emits `success` (with the created guest) and `cancel`.
 */
import { computed, ref } from 'vue'
import Button from '@/components/Button.vue'
import {
  receptionApi,
  type CleaningPreference,
  type Guest,
  type Proximity,
  type Room,
  type RoomType
} from '@/api/reception'
import { useToastStore } from '@/stores/toast'
import { parseApiError } from '@/composables/useOptimistic'

const props = defineProps<{ room?: Room | null }>()
const emit = defineEmits<{ success: [guest: Guest]; cancel: [] }>()

const toast = useToastStore()

const TYPE_UZ: Record<string, string> = {
  single: 'Bir kishilik',
  double: 'Ikki kishilik',
  suite: 'Lyuks',
  accessible: 'Nogironlar uchun'
}
const PROXIMITY_UZ: Record<string, string> = {
  elevator: 'Lift yonida',
  stairs: 'Zinapoya yonida'
}

const isDirect = computed(() => !!props.room)

const form = ref({
  full_name: '',
  phone: '',
  passport_number: '',
  room_type: (props.room?.room_type ?? 'double') as RoomType,
  nights: 1,
  floor_preference: '' as '' | '1' | '2',
  proximity_preference: '' as '' | Proximity,
  cleaning_preference: 'afternoon' as CleaningPreference,
  cleaning_preference_note: ''
})

const submitting = ref(false)
const error = ref<string | null>(null)
const errorDetail = ref<{ room_type?: string } | null>(null)

function money(minor: number) { return `$${(minor / 100).toFixed(2)}` }

async function submit() {
  error.value = null
  errorDetail.value = null
  submitting.value = true
  try {
    const noteValue = form.value.cleaning_preference_note.trim() || undefined
    const result = await receptionApi.checkIn(
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
            floor_preference: form.value.floor_preference
              ? Number(form.value.floor_preference)
              : undefined,
            proximity_preference: form.value.proximity_preference || undefined,
            cleaning_preference: form.value.cleaning_preference,
            cleaning_preference_note: noteValue
          }
    )
    toast.success(`#${result.room_number}-xona ${result.full_name} ga tayinlandi`)
    emit('success', result)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { error?: string; room_type?: string; message?: string } } }
    const data = err.response?.data
    if (data?.error === 'no_rooms_available') {
      error.value = 'So‘ralgan turdagi toza xona hozirda mavjud emas.'
      errorDetail.value = { room_type: data.room_type }
    } else if (data?.error === 'room_not_available') {
      error.value = 'Bu xona endi bo‘sh emas — boshqa kimdir band qildi yoki tozalanmoqda.'
    } else {
      error.value = parseApiError(e)
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <form class="form" @submit.prevent="submit" novalidate>
    <!-- Direct-assignment banner -->
    <div v-if="isDirect && room" class="room-banner">
      <div class="banner-num">
        <span class="num">#{{ room.room_number }}</span>
        <span class="floor">{{ room.floor }}-qavat</span>
      </div>
      <div class="banner-meta">
        <span>{{ TYPE_UZ[room.room_type] || room.room_type }}</span>
        <span class="text-muted">·</span>
        <span class="text-muted">{{ PROXIMITY_UZ[room.proximity] || room.proximity }}</span>
        <span class="text-muted">·</span>
        <span class="tabular">{{ money(room.nightly_rate_minor_units) }} / tun</span>
      </div>
    </div>

    <fieldset class="group">
      <legend>Mehmon</legend>
      <label class="field">
        <span>To‘liq ism</span>
        <input v-model="form.full_name" class="input" type="text" required minlength="2" maxlength="120" autocomplete="name" />
      </label>
      <label class="field">
        <span>Telefon raqami</span>
        <input v-model="form.phone" class="input" type="tel" required placeholder="+998901234567" />
      </label>
      <label class="field full">
        <span>Pasport raqami <span class="text-muted">(ixtiyoriy)</span></span>
        <input v-model="form.passport_number" class="input" type="text" maxlength="40" />
      </label>
    </fieldset>

    <fieldset class="group">
      <legend>Qolish</legend>
      <label v-if="!isDirect" class="field">
        <span>Xona turi</span>
        <select v-model="form.room_type" class="select" required>
          <option value="single">Bir kishilik</option>
          <option value="double">Ikki kishilik</option>
          <option value="suite">Lyuks</option>
          <option value="accessible">Nogironlar uchun</option>
        </select>
      </label>
      <label class="field" :class="{ full: isDirect }">
        <span>Tunlar soni</span>
        <input v-model.number="form.nights" class="input" type="number" min="1" max="365" required />
      </label>
    </fieldset>

    <fieldset class="group">
      <legend>Tozalash afzalligi</legend>
      <label class="field">
        <span>Vaqt</span>
        <select v-model="form.cleaning_preference" class="select">
          <option value="morning">Ertalab</option>
          <option value="afternoon">Tushdan keyin</option>
          <option value="evening">Kechqurun</option>
          <option value="custom">Maxsus</option>
        </select>
      </label>
      <label class="field" v-if="form.cleaning_preference === 'custom'">
        <span>Izoh</span>
        <input v-model="form.cleaning_preference_note" class="input" type="text" maxlength="200" placeholder="masalan: 10:30 sharp" />
      </label>
    </fieldset>

    <fieldset v-if="!isDirect" class="group">
      <legend>Afzalliklar <span class="text-muted text-caption">(ixtiyoriy)</span></legend>
      <label class="field">
        <span>Qavat</span>
        <select v-model="form.floor_preference" class="select">
          <option value="">Afzallik yo‘q</option>
          <option value="1">1-qavat</option>
          <option value="2">2-qavat</option>
        </select>
      </label>
      <label class="field">
        <span>Joylashuv</span>
        <select v-model="form.proximity_preference" class="select">
          <option value="">Afzallik yo‘q</option>
          <option value="elevator">Lift yonida</option>
          <option value="stairs">Zinapoya yonida</option>
        </select>
      </label>
    </fieldset>

    <div v-if="error" class="error" role="alert">
      {{ error }}
      <span v-if="errorDetail?.room_type" class="error-hint">
        Boshqa xona turini tanlang yoki tozalash navbatining tugashini kuting.
      </span>
    </div>

    <div class="row-foot">
      <Button variant="ghost" size="md" type="button" :disabled="submitting" @click="emit('cancel')">Bekor qilish</Button>
      <Button type="submit" variant="primary" size="md" :loading="submitting">
        {{ submitting ? 'Tayinlanmoqda…' : isDirect ? `#${room?.room_number}-xonaga qabul qilish` : 'Qabul qilish' }}
      </Button>
    </div>
  </form>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: 20px; }

.room-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 14px;
  background: var(--primary-soft-1);
  border: 1px solid color-mix(in oklch, var(--primary) 22%, transparent);
  border-radius: 10px;
}
.banner-num { display: flex; flex-direction: column; line-height: 1.1; flex-shrink: 0; }
.banner-num .num {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 22px;
  color: var(--primary-strong);
  letter-spacing: -0.02em;
}
.banner-num .floor { font-size: var(--font-size-xs); color: var(--primary-strong); opacity: 0.7; }
.banner-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-sm);
  color: var(--ink-700);
}

.group {
  border: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.group legend {
  grid-column: 1 / -1;
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted-fg);
  font-weight: 600;
  margin-bottom: 2px;
}
.field.full { grid-column: 1 / -1; }

.error {
  padding: 11px 14px;
  background: color-mix(in srgb, var(--danger) 10%, transparent);
  color: var(--danger);
  border-radius: 10px;
  font-size: var(--font-size-sm);
}
.error-hint { display: block; margin-top: 4px; color: var(--muted-fg); }

.row-foot { display: flex; justify-content: flex-end; gap: 8px; padding-top: 4px; }
</style>
