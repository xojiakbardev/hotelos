<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import Button from '@/components/Button.vue'
import StatCard from '@/components/StatCard.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import Modal from '@/components/Modal.vue'
import CheckInForm from './CheckInForm.vue'
import { receptionApi, type Guest } from '@/api/reception'
import { useGuestsStore } from '@/stores/guests'
import { useWsStore } from '@/stores/ws'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { parseApiError, useOptimistic } from '@/composables/useOptimistic'
import { ROOM_TYPE_UZ } from '@/lib/labels'

const guests = useGuestsStore()
const ws = useWsStore()
const auth = useAuthStore()
const toast = useToastStore()

onMounted(() => guests.load())

watch(
  () => ws.lastEvent,
  (env) => {
    const ch = env?.channel ?? ''
    if (ch.startsWith('guests.') || ch.startsWith('bills.')) guests.load()
  }
)

const canCheckOut = computed(() => auth.role === 'manager' || auth.role === 'reception')

const confirmGuest = ref<Guest | null>(null)
const checkInOpen = ref(false)

const totalRevenuePotential = computed(() =>
  guests.guests.reduce((s, g) => s + g.nightly_rate_locked_minor_units, 0)
)

function money(minor: number) { return `$${(minor / 100).toFixed(2)}` }

function nightsSoFar(g: Guest) {
  const ms = Date.now() - new Date(g.checked_in_at).getTime()
  return Math.max(1, Math.ceil(ms / (24 * 3600 * 1000)))
}

async function doCheckOut(g: Guest) {
  confirmGuest.value = null
  const snapshot = [...guests.guests]
  const run = useOptimistic({
    apply: () => guests.removeById(g.id),
    revert: () => { guests.guests = snapshot },
    call: () => receptionApi.checkOut(g.id),
    successMsg: (bill) =>
      `#${bill.room_number}-xona jo‘natildi — ${bill.nights} tun, jami ${money(bill.total_minor_units)}`,
    errorMsg: (e) => `Xato: ${parseApiError(e)}`
  })
  const bill = await run()
  if (bill) toast.info(`Hisob ${bill.bill_id.slice(0, 8)}… saqlandi`)
}

function onCheckInSuccess() {
  checkInOpen.value = false
  guests.load()
}
</script>

<template>
  <div class="page">
    <PageHeader title="Faol mehmonlar">
      <template #actions>
        <Button v-if="canCheckOut" variant="primary" size="md" @click="checkInOpen = true">
          Mehmonni qabul qilish
        </Button>
      </template>
    </PageHeader>

    <section class="stats">
      <StatCard label="Faol mehmonlar" :value="guests.guests.length" hint="Hozir mehmonxonada" tone="primary" />
      <StatCard
        label="Tunlik potentsial"
        :value="money(totalRevenuePotential)"
        hint="Barcha aktiv xonalar yig‘indisi"
        tone="success"
      />
    </section>

    <section v-if="guests.error" class="error">{{ guests.error }}</section>
    <section v-if="guests.loading && !guests.guests.length" class="empty card-paper">Mehmonlar yuklanmoqda…</section>
    <section v-else-if="!guests.guests.length" class="empty card-paper">
      Hozircha faol mehmonlar yo‘q. Mehmonxonada sokin payt.
    </section>

    <article v-else class="card-paper table-wrap">
      <table class="data">
        <thead>
          <tr>
            <th>Mehmon</th>
            <th>Telefon</th>
            <th>Xona</th>
            <th>Turi</th>
            <th>Qabul qilindi</th>
            <th class="num">Tunlar</th>
            <th class="num">Tunlik narx</th>
            <th v-if="canCheckOut" class="num">Harakat</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="g in guests.guests" :key="g.id">
            <td>
              <div class="cell-name">
                <span class="avatar">{{ g.full_name.slice(0, 1).toUpperCase() }}</span>
                <span class="name">{{ g.full_name }}</span>
              </div>
            </td>
            <td class="mono text-muted">{{ g.phone }}</td>
            <td class="mono">#{{ g.room_number }} <span class="text-muted">/ {{ g.floor }}-qavat</span></td>
            <td>{{ ROOM_TYPE_UZ[g.room_type] || g.room_type }}</td>
            <td class="text-muted">{{ new Date(g.checked_in_at).toLocaleString('uz-UZ') }}</td>
            <td class="num mono tabular">{{ nightsSoFar(g) }}</td>
            <td class="num mono tabular">{{ money(g.nightly_rate_locked_minor_units) }}</td>
            <td v-if="canCheckOut" class="num">
              <Button variant="outline" size="sm" @click="confirmGuest = g">Jo‘natish</Button>
            </td>
          </tr>
        </tbody>
      </table>
    </article>

    <ConfirmDialog
      :open="confirmGuest !== null"
      :title="confirmGuest ? `${confirmGuest.full_name} ni jo‘natish` : ''"
      :message="confirmGuest
        ? `#${confirmGuest.room_number}-xonaning hisobi yakunlanadi va tozalash navbatiga qo‘shiladi.`
        : ''"
      confirm-label="Jo‘natish"
      cancel-label="Bekor qilish"
      tone="primary"
      @cancel="confirmGuest = null"
      @confirm="confirmGuest && doCheckOut(confirmGuest)"
    />

    <Modal :open="checkInOpen" title="Mehmonni qabul qilish" size="lg" @close="checkInOpen = false">
      <CheckInForm @cancel="checkInOpen = false" @success="onCheckInSuccess" />
    </Modal>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
}

.error {
  padding: 14px;
  background: color-mix(in srgb, var(--danger) 10%, transparent);
  color: var(--danger);
  border-radius: var(--radius-md);
}
.empty { padding: 48px; text-align: center; color: var(--muted-fg); }

.table-wrap { padding: 0; overflow: hidden; }

.data {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}
.data th, .data td {
  padding: 12px 18px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}
.data thead th {
  background: var(--bg-subtle);
  font-weight: 600;
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted-fg);
}
.data tbody tr:last-child td { border-bottom: none; }
.data tbody tr:hover { background: var(--bg-subtle); }
.data .num { text-align: right; }
.mono { font-family: var(--font-mono); }

.cell-name { display: flex; align-items: center; gap: 10px; }
.avatar {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  background: var(--primary-soft-2);
  color: var(--primary-strong);
  display: grid;
  place-items: center;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--font-size-xs);
  flex-shrink: 0;
}
.name { font-weight: 500; color: var(--ink-900); }
</style>
