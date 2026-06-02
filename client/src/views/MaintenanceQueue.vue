<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import Button from '@/components/Button.vue'
import StatCard from '@/components/StatCard.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import Modal from '@/components/Modal.vue'
import MaintenanceReport from './MaintenanceReport.vue'
import { maintenanceApi, type Issue } from '@/api/maintenance'
import { useMaintenanceStore } from '@/stores/maintenance'
import { useWsStore } from '@/stores/ws'
import { useAuthStore } from '@/stores/auth'
import { parseApiError, useOptimistic } from '@/composables/useOptimistic'
import { URGENCY_UZ } from '@/lib/labels'

const store = useMaintenanceStore()
const ws = useWsStore()
const auth = useAuthStore()

const reportOpen = ref(false)

onMounted(() => store.load())

watch(
  () => ws.lastEvent,
  (env) => { if (env?.channel?.startsWith('maintenance.')) store.load() }
)

const canReport = computed(() => auth.role === 'manager' || auth.role === 'reception')
const canWork = computed(() => auth.role === 'manager' || auth.role === 'technician')
const unassigned = computed(() => store.unassigned)
const mine = computed(() => store.mine.filter((i) => i.status !== 'resolved'))

const counts = computed(() => {
  const by = (u: string) => unassigned.value.filter((i) => i.urgency === u).length
  return { critical: by('critical'), high: by('high'), normal: by('normal'), low: by('low'), mine: mine.value.length }
})

async function claim(issue: Issue) {
  const before = { ...issue }
  const run = useOptimistic({
    apply: () => {
      issue.status = 'assigned'
      issue.assigned_technician_id = auth.user?.id ?? null
      issue.assigned_at = new Date().toISOString()
    },
    revert: () => Object.assign(issue, before),
    call: () => maintenanceApi.claim(issue.id),
    ok: (u) => store.upsert(u),
    successMsg: (u) => `#${u.room_number}-xona qabul qilindi (${URGENCY_UZ[u.urgency] ?? u.urgency})`,
    errorMsg: (e) => `Xato: ${parseApiError(e)}`
  })
  await run()
}

async function resolve(issue: Issue) {
  const before = { ...issue }
  const run = useOptimistic({
    apply: () => { issue.status = 'resolved'; issue.resolved_at = new Date().toISOString() },
    revert: () => Object.assign(issue, before),
    call: () => maintenanceApi.resolve(issue.id),
    ok: (u) => store.removeById(u.id),
    successMsg: (u) => `#${u.room_number}-xona muammosi hal qilindi`,
    errorMsg: (e) => `Xato: ${parseApiError(e)}`
  })
  await run()
}

function onReported() {
  reportOpen.value = false
  store.load()
}
</script>

<template>
  <div class="page">
    <PageHeader title="Texnik xizmat">
      <template #actions>
        <Button v-if="canReport" variant="primary" size="md" @click="reportOpen = true">Muammo qayd etish</Button>
      </template>
    </PageHeader>

    <section class="stats">
      <StatCard label="Kritik" :value="counts.critical" hint="Darhol kerak" tone="danger" />
      <StatCard label="Yuqori" :value="counts.high" hint="Bugun" tone="warn" />
      <StatCard label="O‘rta" :value="counts.normal" hint="24 soat ichida" tone="primary" />
      <StatCard label="Past" :value="counts.low" hint="Shoshilinch emas" />
      <StatCard v-if="canWork" label="Menga tegishli" :value="counts.mine" hint="Hal qilish kutmoqda" tone="primary" />
    </section>

    <section v-if="store.error" class="error">{{ store.error }}</section>
    <section v-if="store.loading && !store.open.length" class="empty card-paper">Yuklanmoqda…</section>

    <template v-else>
      <template v-if="canWork || mine.length">
        <div class="section-divider">Mening navbatim</div>
        <article v-if="!mine.length" class="empty card-paper">Hozircha sizga tayinlangan muammo yo‘q.</article>
        <article v-else class="card-paper table-wrap">
          <table class="data">
            <thead>
              <tr>
                <th>Xona</th>
                <th>Daraja</th>
                <th>Tavsif</th>
                <th>Tayinlandi</th>
                <th v-if="canWork" class="num">Harakat</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="i in mine" :key="i.id">
                <td class="mono">#{{ i.room_number }} <span class="text-muted">/ {{ i.floor }}-qavat</span></td>
                <td><StatusBadge :tone="i.urgency" /></td>
                <td class="desc-cell">{{ i.description }}</td>
                <td class="text-muted">{{ i.assigned_at ? new Date(i.assigned_at).toLocaleTimeString('uz-UZ') : '—' }}</td>
                <td v-if="canWork" class="num">
                  <Button variant="success" size="sm" @click="resolve(i)">Hal qilindi</Button>
                </td>
              </tr>
            </tbody>
          </table>
        </article>
      </template>

      <div class="section-divider">Ustuvor navbat (tayinlanmagan)</div>
      <article v-if="!unassigned.length" class="empty card-paper">Ochiq muammolar yo‘q — sokin kun.</article>
      <article v-else class="card-paper table-wrap">
        <table class="data">
          <thead>
            <tr>
              <th>Xona</th>
              <th>Daraja</th>
              <th>Tavsif</th>
              <th>Qayd etildi</th>
              <th v-if="canWork" class="num">Harakat</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="i in unassigned" :key="i.id">
              <td class="mono">#{{ i.room_number }} <span class="text-muted">/ {{ i.floor }}-qavat</span></td>
              <td><StatusBadge :tone="i.urgency" /></td>
              <td class="desc-cell">{{ i.description }}</td>
              <td class="text-muted">{{ new Date(i.reported_at).toLocaleTimeString('uz-UZ') }}</td>
              <td v-if="canWork" class="num">
                <Button variant="primary" size="sm" @click="claim(i)">Qabul qilish</Button>
              </td>
            </tr>
          </tbody>
        </table>
      </article>
    </template>

    <Modal :open="reportOpen" title="Muammo qayd etish" size="md" @close="reportOpen = false">
      <MaintenanceReport @cancel="reportOpen = false" @success="onReported" />
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

.error {
  padding: 14px;
  background: color-mix(in srgb, var(--danger) 10%, transparent);
  color: var(--danger);
  border-radius: var(--radius-md);
}
.empty { padding: 32px; text-align: center; color: var(--muted-fg); }

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
.desc-cell {
  max-width: 380px;
  color: var(--ink-700);
  line-height: 1.4;
}
</style>
