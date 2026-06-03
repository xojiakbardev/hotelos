<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import Button from '@/components/Button.vue'
import Modal from '@/components/Modal.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { reservationsApi, type Reservation, type ReservationStatus } from '@/api/reservations'
import { receptionApi, type Room } from '@/api/reception'
import { useToastStore } from '@/stores/toast'
import { useWsStore } from '@/stores/ws'
import { parseApiError } from '@/composables/useOptimistic'

const items = ref<Reservation[]>([])
const rooms = ref<Room[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const filter = ref<'all' | ReservationStatus>('all')

const toast = useToastStore()
const ws = useWsStore()

const createOpen = ref(false)
const toCancel = ref<Reservation | null>(null)

const draft = ref({
  full_name: '',
  phone: '',
  passport_number: '',
  room_id: '',
  check_in_date: '',
  check_out_date: ''
})
const submitting = ref(false)

const STATUS_LABELS: Record<ReservationStatus, string> = {
  pending: 'Kutilmoqda',
  confirmed: 'Tasdiqlangan',
  checked_in: 'Qabul qilingan',
  cancelled: 'Bekor qilingan',
  no_show: 'Kelmadi'
}

const visible = computed(() =>
  filter.value === 'all' ? items.value : items.value.filter((r) => r.status === filter.value)
)

function money(minor: number) { return `$${(minor / 100).toFixed(2)}` }

function nights(r: Reservation) {
  const ms = new Date(r.check_out_date).getTime() - new Date(r.check_in_date).getTime()
  return Math.max(1, Math.round(ms / 86400000))
}

async function load() {
  loading.value = true
  try {
    const [rs, rms] = await Promise.all([reservationsApi.list(), receptionApi.listRooms()])
    items.value = rs
    rooms.value = rms.rooms
  } catch (e: unknown) {
    error.value = parseApiError(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)

watch(
  () => ws.lastEvent,
  (env) => { if (env?.channel?.startsWith('reservations.')) load() }
)

function openCreate() {
  const today = new Date().toISOString().slice(0, 10)
  const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10)
  draft.value = {
    full_name: '',
    phone: '',
    passport_number: '',
    room_id: '',
    check_in_date: today,
    check_out_date: tomorrow
  }
  createOpen.value = true
}

async function submitCreate() {
  submitting.value = true
  try {
    const created = await reservationsApi.create({
      full_name: draft.value.full_name.trim(),
      phone: draft.value.phone.trim(),
      passport_number: draft.value.passport_number.trim() || undefined,
      room_id: draft.value.room_id,
      check_in_date: draft.value.check_in_date,
      check_out_date: draft.value.check_out_date
    })
    items.value = [created, ...items.value]
    toast.success(`#${created.room_number}-xona uchun bron yaratildi`)
    createOpen.value = false
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: { error?: string } } } }
    const code = err.response?.data?.detail?.error
    if (code === 'room_unavailable_for_dates') {
      toast.error('Bu xona tanlangan sanalar uchun band — boshqa xona yoki sana tanlang.')
    } else {
      toast.error(parseApiError(e))
    }
  } finally {
    submitting.value = false
  }
}

async function confirm(r: Reservation) {
  try {
    const updated = await reservationsApi.confirm(r.id)
    Object.assign(r, updated)
    toast.success(`Bron tasdiqlandi`)
  } catch (e) { toast.error(parseApiError(e)) }
}

async function noShow(r: Reservation) {
  try {
    const updated = await reservationsApi.noShow(r.id)
    Object.assign(r, updated)
    toast.info(`Mehmon kelmadi deb belgilandi`)
  } catch (e) { toast.error(parseApiError(e)) }
}

async function checkIn(r: Reservation) {
  try {
    await reservationsApi.checkIn(r.id)
    toast.success(`Mehmon #${r.room_number}-xonaga joylashtirildi`)
    await load()
  } catch (e) { toast.error(parseApiError(e)) }
}

async function doCancel() {
  if (!toCancel.value) return
  try {
    const updated = await reservationsApi.cancel(toCancel.value.id)
    Object.assign(toCancel.value, updated)
    toast.info('Bron bekor qilindi')
  } catch (e) { toast.error(parseApiError(e)) }
  finally { toCancel.value = null }
}
</script>

<template>
  <div class="page">
    <PageHeader title="Bronlar">
      <template #actions>
        <Button variant="primary" size="md" @click="openCreate">+ Yangi bron</Button>
      </template>
    </PageHeader>

    <section class="filters card-paper">
      <label class="field inline">
        <span>Status</span>
        <select v-model="filter" class="select">
          <option value="all">Barchasi</option>
          <option v-for="(label, key) in STATUS_LABELS" :key="key" :value="key">{{ label }}</option>
        </select>
      </label>
    </section>

    <section v-if="error" class="error">{{ error }}</section>
    <section v-if="loading" class="empty card-paper">Yuklanmoqda…</section>
    <section v-else-if="!visible.length" class="empty card-paper">Bronlar topilmadi.</section>

    <article v-else class="card-paper table-wrap">
      <table class="data">
        <thead>
          <tr>
            <th>Mehmon</th>
            <th>Telefon</th>
            <th>Xona</th>
            <th>Kirish</th>
            <th>Chiqish</th>
            <th class="num">Tunlar</th>
            <th class="num">Tunlik</th>
            <th>Status</th>
            <th class="num">Harakat</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in visible" :key="r.id">
            <td>{{ r.full_name }}</td>
            <td class="mono text-muted">{{ r.phone }}</td>
            <td>#{{ r.room_number }} <span class="text-muted">/ {{ r.floor }}-q</span></td>
            <td>{{ r.check_in_date }}</td>
            <td>{{ r.check_out_date }}</td>
            <td class="num tabular">{{ nights(r) }}</td>
            <td class="num mono tabular">{{ money(r.nightly_rate_locked_minor_units) }}</td>
            <td><StatusBadge :tone="r.status" :label="STATUS_LABELS[r.status]" /></td>
            <td class="num actions">
              <Button v-if="r.status === 'pending'" size="sm" variant="primary" @click="confirm(r)">Tasdiqlash</Button>
              <Button v-if="r.status === 'pending' || r.status === 'confirmed'" size="sm" variant="success" @click="checkIn(r)">Check-in</Button>
              <Button v-if="r.status === 'pending' || r.status === 'confirmed'" size="sm" variant="ghost" @click="toCancel = r">Bekor</Button>
              <Button v-if="r.status === 'pending' || r.status === 'confirmed'" size="sm" variant="ghost" @click="noShow(r)">Kelmadi</Button>
            </td>
          </tr>
        </tbody>
      </table>
    </article>

    <Modal :open="createOpen" title="Yangi bron yaratish" size="md" @close="createOpen = false">
      <form class="form" @submit.prevent="submitCreate">
        <div class="row">
          <label class="field"><span>To‘liq ism</span><input v-model="draft.full_name" class="input" type="text" required minlength="2" maxlength="120" /></label>
          <label class="field"><span>Telefon</span><input v-model="draft.phone" class="input" type="tel" required placeholder="+998901234567" /></label>
        </div>
        <label class="field"><span>Pasport (ixtiyoriy)</span><input v-model="draft.passport_number" class="input" type="text" maxlength="40" /></label>
        <label class="field"><span>Xona</span>
          <select v-model="draft.room_id" class="select" required>
            <option value="" disabled>Xonani tanlang</option>
            <option v-for="r in rooms" :key="r.id" :value="r.id">
              #{{ r.room_number }} — {{ r.room_type }} ({{ r.floor }}-qavat, {{ money(r.nightly_rate_minor_units) }}/tun)
            </option>
          </select>
        </label>
        <div class="row">
          <label class="field"><span>Kirish sanasi</span><input v-model="draft.check_in_date" class="input" type="date" required /></label>
          <label class="field"><span>Chiqish sanasi</span><input v-model="draft.check_out_date" class="input" type="date" required /></label>
        </div>
        <div class="row-foot">
          <Button variant="ghost" type="button" :disabled="submitting" @click="createOpen = false">Bekor</Button>
          <Button type="submit" variant="primary" :loading="submitting">Bron qilish</Button>
        </div>
      </form>
    </Modal>

    <ConfirmDialog
      :open="toCancel !== null"
      :title="toCancel ? `${toCancel.full_name} bronini bekor qilish?` : ''"
      message="Bron bekor qilinsa, xona boshqa sana uchun bo‘shaydi."
      confirm-label="Bekor qilish"
      cancel-label="Yopish"
      tone="destructive"
      @cancel="toCancel = null"
      @confirm="doCancel"
    />
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.filters { padding: 12px 16px; display: flex; gap: 16px; align-items: center; }
.field.inline { display: flex; flex-direction: row; align-items: center; gap: 8px; }
.error { padding: 14px; background: color-mix(in srgb, var(--danger) 10%, transparent); color: var(--danger); border-radius: var(--radius-md); }
.empty { padding: 48px; text-align: center; color: var(--muted-fg); }
.table-wrap { padding: 0; overflow: hidden; }
.data { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.data th, .data td { padding: 12px 14px; text-align: left; border-bottom: 1px solid var(--border); }
.data thead th { background: var(--bg-subtle); font-weight: 600; font-size: var(--font-size-xs); text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted-fg); }
.data tbody tr:last-child td { border-bottom: none; }
.data .num { text-align: right; }
.mono { font-family: var(--font-mono); }
.tabular { font-variant-numeric: tabular-nums; }
.actions { display: flex; gap: 6px; justify-content: flex-end; flex-wrap: wrap; }

.form { display: flex; flex-direction: column; gap: 12px; }
.form .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.row-foot { display: flex; justify-content: flex-end; gap: 8px; padding-top: 4px; }
</style>
