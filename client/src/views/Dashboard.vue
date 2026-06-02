<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import GuestsChart from '@/components/GuestsChart.vue'
import { useAuthStore } from '@/stores/auth'
import { useWsStore } from '@/stores/ws'
import { useRoomsStore } from '@/stores/rooms'
import { useHousekeepingStore } from '@/stores/housekeeping'
import { useOrdersStore } from '@/stores/orders'
import { useMaintenanceStore } from '@/stores/maintenance'
import { useGuestsStore } from '@/stores/guests'
import { EVENT_UZ } from '@/lib/labels'

const auth = useAuthStore()
const ws = useWsStore()
const rooms = useRoomsStore()
const guests = useGuestsStore()
const housekeeping = useHousekeepingStore()
const orders = useOrdersStore()
const maintenance = useMaintenanceStore()

const ROLE_UZ: Record<string, string> = {
  manager: 'Boshqaruvchi',
  reception: 'Qabulchi',
  technician: 'Texnik',
  cleaner: 'Tozalovchi'
}

onMounted(() => {
  rooms.load()
  if (auth.role === 'manager' || auth.role === 'reception') {
    guests.load()
    orders.load()
  }
  if (auth.role === 'manager' || auth.role === 'cleaner') {
    housekeeping.load()
  }
  if (auth.role !== 'cleaner') {
    maintenance.load()
  }
})

// Live reconciliation — any room/guest/order/maintenance/cleaning event
// invalidates and refetches the relevant store.
watch(
  () => ws.lastEvent,
  (env) => {
    const ch = env?.channel ?? ''
    if (ch.startsWith('rooms.') || ch.startsWith('guests.')) rooms.load()
    if (ch.startsWith('guests.')) guests.load()
    if (ch.startsWith('rooms.')) housekeeping.load()
    if (ch.startsWith('orders.')) orders.load()
    if (ch.startsWith('maintenance.')) maintenance.load()
  }
)

const greeting = computed(() => {
  const name = auth.user?.full_name || auth.user?.phone || ''
  return name ? `Xush kelibsiz, ${name}` : 'Xush kelibsiz'
})

const roomsAvailable = computed(() => rooms.available.length)
const roomsOccupied  = computed(() => rooms.rooms.filter((r) => r.status === 'occupied').length)
const roomsTotal     = computed(() => rooms.rooms.length)
const cleaningOpen   = computed(() => housekeeping.pending.length + housekeeping.inProgress.length)
const ordersOpen     = computed(() => orders.open.length)
const openIssues     = computed(() => maintenance.open.length)
</script>

<template>
  <div class="page">
    <PageHeader title="Boshqaruv paneli" />

    <section class="stats">
      <StatCard
        label="Bo‘sh xonalar"
        :value="`${roomsAvailable} / ${roomsTotal}`"
        :hint="`Band: ${roomsOccupied}`"
        tone="success"
      />
      <StatCard
        v-if="auth.role === 'manager' || auth.role === 'reception'"
        label="Faol mehmonlar"
        :value="guests.guests.length"
        hint="Hozir mehmonxonada"
        tone="primary"
      />
      <StatCard
        v-if="auth.role === 'manager' || auth.role === 'cleaner'"
        label="Tozalash navbati"
        :value="cleaningOpen"
        :hint="`Kutmoqda: ${housekeeping.pending.length} · Bajarilmoqda: ${housekeeping.inProgress.length}`"
        tone="warn"
      />
      <StatCard
        v-if="auth.role === 'manager' || auth.role === 'reception'"
        label="Ochiq buyurtmalar"
        :value="ordersOpen"
        hint="Xona xizmati"
        tone="primary"
      />
      <StatCard
        v-if="auth.role !== 'cleaner'"
        label="Texnik muammolar"
        :value="openIssues"
        hint="Ochiq holatda"
        :tone="openIssues > 0 ? 'danger' : 'success'"
      />
    </section>

    <GuestsChart :days="30" :height="200" />

    <section class="grid-2">
      <article class="card-paper events">
        <header class="card-head">
          <h2>Jonli oqim</h2>
          <span class="text-caption text-muted">Oxirgi {{ ws.eventLog.length }} ta hodisa</span>
        </header>
        <ul v-if="ws.eventLog.length" class="event-list">
          <li
            v-for="(e, idx) in ws.eventLog.slice(0, 12)"
            :key="idx"
            class="event-row"
          >
            <span class="event-name">{{ EVENT_UZ[e.event] || e.event }}</span>
            <span class="text-caption text-muted mono-channel">{{ e.channel || '—' }}</span>
            <span class="text-caption text-muted tabular">
              {{ e.occurred_at ? new Date(e.occurred_at).toLocaleTimeString() : '' }}
            </span>
          </li>
        </ul>
        <div v-else class="empty">
          Hodisalar hali yo‘q. Tizimda harakat boshlanganda bu yerda paydo bo‘ladi.
        </div>
      </article>

      <article class="card-paper status">
        <header class="card-head">
          <h2>Aloqa</h2>
          <StatusBadge :tone="ws.connected ? 'clean' : 'maintenance'" :label="ws.connected ? 'Faol' : 'Uzilgan'" />
        </header>
        <dl class="meta">
          <div>
            <dt>Rol</dt>
            <dd>{{ ROLE_UZ[auth.role || ''] || auth.role || '—' }}</dd>
          </div>
          <div>
            <dt>Telefon</dt>
            <dd class="tabular">{{ auth.user?.phone || '—' }}</dd>
          </div>
          <div>
            <dt>Aloqa holati</dt>
            <dd>{{ ws.connected ? 'WebSocket faol' : 'WebSocket aloqasiz' }}</dd>
          </div>
        </dl>
      </article>
    </section>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 20px; }

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.grid-2 {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  gap: 16px;
}
@media (max-width: 960px) {
  .grid-2 { grid-template-columns: 1fr; }
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}
.card-head h2 {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--ink-800);
}
.events { padding: 0; }
.status { padding: 0; }

.event-list {
  list-style: none;
  margin: 0;
  padding: 6px 0;
  max-height: 360px;
  overflow-y: auto;
}
.event-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 80px;
  gap: 12px;
  padding: 9px 20px;
  font-size: var(--font-size-sm);
  align-items: center;
}
.event-row:hover { background: var(--bg-subtle); }
.event-name {
  color: var(--primary-strong);
  font-weight: 600;
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
}

.empty {
  padding: 32px 20px;
  text-align: center;
  color: var(--muted-fg);
  font-size: var(--font-size-sm);
}

.meta {
  margin: 0;
  padding: 12px 20px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.meta > div {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
}
.meta > div:last-child { border-bottom: none; }
.meta dt {
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted-fg);
  font-weight: 600;
}
.meta dd {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--ink-800);
}
</style>
