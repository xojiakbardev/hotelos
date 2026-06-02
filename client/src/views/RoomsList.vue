<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import Button from '@/components/Button.vue'
import StatCard from '@/components/StatCard.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import Modal from '@/components/Modal.vue'
import CheckInForm from './CheckInForm.vue'
import { type Room } from '@/api/reception'
import { useRoomsStore } from '@/stores/rooms'
import { useWsStore } from '@/stores/ws'
import { useAuthStore } from '@/stores/auth'

const rooms = useRoomsStore()
const ws = useWsStore()
const auth = useAuthStore()

const filterStatus = ref<string>('all')
const filterType = ref<string>('all')

// `checkInRoom` = a specific room the user clicked; `null` means "open
// the modal in algorithm mode" (no room targeted).
const checkInOpen = ref(false)
const checkInRoom = ref<Room | null>(null)

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

const visible = computed(() =>
  rooms.rooms.filter((r) => {
    if (filterStatus.value !== 'all' && r.status !== filterStatus.value) return false
    if (filterType.value !== 'all' && r.room_type !== filterType.value) return false
    return true
  })
)

const counts = computed(() => {
  const total = rooms.rooms.length
  const available = rooms.rooms.filter((r) => r.status === 'available' && r.cleanliness_status === 'clean').length
  const occupied = rooms.rooms.filter((r) => r.status === 'occupied').length
  const cleaning = rooms.rooms.filter((r) => r.cleanliness_status === 'cleaning').length
  const maintenance = rooms.rooms.filter((r) => r.cleanliness_status === 'maintenance').length
  return { total, available, occupied, cleaning, maintenance }
})

onMounted(() => rooms.load())

watch(
  () => ws.lastEvent,
  (env) => {
    const ch = env?.channel ?? ''
    if (ch.startsWith('rooms.') || ch.startsWith('guests.')) rooms.load()
  }
)

const canCheckIn = computed(() => auth.role === 'manager' || auth.role === 'reception')

function isAssignable(r: Room) {
  return r.status === 'available' && r.cleanliness_status === 'clean'
}

function money(minor: number) { return `$${(minor / 100).toFixed(2)}` }

function openTopButton() {
  checkInRoom.value = null
  checkInOpen.value = true
}

function openForRoom(r: Room) {
  if (!canCheckIn.value || !isAssignable(r)) return
  checkInRoom.value = r
  checkInOpen.value = true
}

function onCheckInSuccess() {
  checkInOpen.value = false
  checkInRoom.value = null
  rooms.load()
}
</script>

<template>
  <div class="page">
    <PageHeader title="Xonalar">
      <template #actions>
        <Button v-if="canCheckIn" variant="primary" size="md" @click="openTopButton">
          Mehmonni qabul qilish
        </Button>
      </template>
    </PageHeader>

    <section class="stats">
      <StatCard label="Jami" :value="counts.total" hint="Inventar" />
      <StatCard label="Bo‘sh" :value="counts.available" hint="Toza va band emas" tone="success" />
      <StatCard label="Band" :value="counts.occupied" hint="Mehmon bilan" tone="primary" />
      <StatCard label="Tozalanmoqda" :value="counts.cleaning" hint="Tozalash navbati" tone="warn" />
      <StatCard label="Texnik xizmatda" :value="counts.maintenance" hint="Muammo ko‘rsatildi" tone="danger" />
    </section>

    <section class="filters card-paper">
      <label class="field inline">
        <span>Holat</span>
        <select v-model="filterStatus" class="select">
          <option value="all">Hammasi</option>
          <option value="available">Bo‘sh</option>
          <option value="occupied">Band</option>
          <option value="out_of_service">Xizmatdan tashqari</option>
        </select>
      </label>
      <label class="field inline">
        <span>Turi</span>
        <select v-model="filterType" class="select">
          <option value="all">Hammasi</option>
          <option value="single">Bir kishilik</option>
          <option value="double">Ikki kishilik</option>
          <option value="suite">Lyuks</option>
          <option value="accessible">Nogironlar uchun</option>
        </select>
      </label>
    </section>

    <section v-if="rooms.error" class="error">{{ rooms.error }}</section>
    <section v-if="rooms.loading && !rooms.rooms.length" class="empty card-paper">Xonalar yuklanmoqda…</section>
    <section v-else-if="!visible.length" class="empty card-paper">Filtrlarga mos xona topilmadi.</section>

    <div v-else class="grid">
      <article
        v-for="r in visible"
        :key="r.id"
        :class="['card-paper', 'room', { 'room--clickable': canCheckIn && isAssignable(r) }]"
        :role="canCheckIn && isAssignable(r) ? 'button' : undefined"
        :tabindex="canCheckIn && isAssignable(r) ? 0 : undefined"
        @click="openForRoom(r)"
        @keydown.enter="openForRoom(r)"
        @keydown.space.prevent="openForRoom(r)"
      >
        <header class="room-head">
          <div class="num-block">
            <span class="num">#{{ r.room_number }}</span>
            <span class="floor">{{ r.floor }}-qavat</span>
          </div>
          <StatusBadge :tone="r.status" />
        </header>
        <div class="room-meta">
          <div class="meta-row"><span class="text-muted text-caption">Turi</span><span>{{ TYPE_UZ[r.room_type] || r.room_type }}</span></div>
          <div class="meta-row"><span class="text-muted text-caption">Tozalik</span><StatusBadge :tone="r.cleanliness_status" /></div>
          <div class="meta-row"><span class="text-muted text-caption">Joylashuv</span><span class="text-muted">{{ PROXIMITY_UZ[r.proximity] || r.proximity }}</span></div>
          <div class="meta-row"><span class="text-muted text-caption">Tunlik narx</span><span class="tabular">{{ money(r.nightly_rate_minor_units) }}</span></div>
        </div>
        <footer class="room-foot">
          <span class="text-muted text-caption">
            Oxirgi tozalash: {{ new Date(r.last_cleaned_at).toLocaleString('uz-UZ') }}
          </span>
          <span v-if="canCheckIn && isAssignable(r)" class="cta">Mehmon qabul qilish →</span>
        </footer>
      </article>
    </div>

    <Modal
      :open="checkInOpen"
      :title="checkInRoom
        ? `#${checkInRoom.room_number}-xonaga mehmon qabul qilish`
        : 'Mehmonni qabul qilish'"
      size="lg"
      @close="checkInOpen = false"
    >
      <CheckInForm
        :room="checkInRoom"
        @cancel="checkInOpen = false"
        @success="onCheckInSuccess"
      />
    </Modal>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
}

.filters {
  display: flex;
  gap: 16px;
  padding: 14px 18px;
}
.field.inline { flex-direction: row; align-items: center; gap: 10px; min-width: 240px; }
.field.inline > span:first-child {
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted-fg);
  font-weight: 600;
  flex-shrink: 0;
}
.field.inline .select { min-width: 160px; }

.error {
  padding: 14px;
  background: color-mix(in srgb, var(--danger) 10%, transparent);
  color: var(--danger);
  border-radius: var(--radius-md);
}
.empty { padding: 48px; text-align: center; color: var(--muted-fg); }

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
}

.room {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: box-shadow var(--motion-fast) var(--motion-ease),
              transform var(--motion-fast) var(--motion-ease),
              border-color var(--motion-fast) var(--motion-ease);
}
.room--clickable {
  cursor: pointer;
}
.room--clickable:hover {
  box-shadow: var(--elev-2);
  transform: translateY(-2px);
  border-color: color-mix(in oklch, var(--primary) 30%, var(--border));
}
.room--clickable:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--primary) 20%, transparent), var(--elev-2);
}

.room-head { display: flex; justify-content: space-between; align-items: flex-start; }
.num-block { display: flex; flex-direction: column; }
.num { font-family: var(--font-display); font-weight: 700; font-size: 22px; color: var(--ink-900); letter-spacing: -0.02em; }
.floor { font-size: var(--font-size-xs); color: var(--muted-fg); margin-top: 2px; }

.room-meta { display: flex; flex-direction: column; gap: 6px; }
.meta-row { display: flex; justify-content: space-between; align-items: center; font-size: var(--font-size-sm); }

.room-foot {
  border-top: 1px solid var(--border);
  padding-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.cta {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--primary-strong);
  opacity: 0;
  transition: opacity var(--motion-fast) var(--motion-ease);
}
.room--clickable:hover .cta,
.room--clickable:focus-visible .cta {
  opacity: 1;
}
</style>
