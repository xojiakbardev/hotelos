<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import Button from '@/components/Button.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { housekeepingApi, type CleaningEntry } from '@/api/housekeeping'
import { useHousekeepingStore } from '@/stores/housekeeping'
import { useWsStore } from '@/stores/ws'
import { useAuthStore } from '@/stores/auth'
import { useOptimistic, parseApiError } from '@/composables/useOptimistic'

const store = useHousekeepingStore()
const ws = useWsStore()
const auth = useAuthStore()

onMounted(() => store.load())

watch(
  () => ws.lastEvent,
  (env) => {
    const ch = env?.channel
    if (!ch) return
    if (ch.startsWith('rooms.') || ch.startsWith('housekeeping.')) store.load()
  }
)

const prefLabels: Record<string, string> = {
  morning: 'Ertalab',
  afternoon: 'Tushdan keyin',
  evening: 'Kechqurun',
  custom: 'Maxsus vaqt'
}

const canWork = computed(() => auth.role === 'manager' || auth.role === 'cleaner')

async function startEntry(entry: CleaningEntry) {
  const before = { ...entry }
  const run = useOptimistic({
    apply: () => { entry.status = 'in_progress'; entry.started_at = new Date().toISOString() },
    revert: () => Object.assign(entry, before),
    call: () => housekeepingApi.start(entry.id),
    ok: (u) => store.upsert(u),
    successMsg: (u) => `#${u.room_number}-xona tozalashi boshlandi`,
    errorMsg: (e) => `Xato: ${parseApiError(e)}`
  })
  await run()
}

async function completeEntry(entry: CleaningEntry) {
  const before = { ...entry }
  const run = useOptimistic({
    apply: () => { entry.status = 'completed'; entry.completed_at = new Date().toISOString() },
    revert: () => Object.assign(entry, before),
    call: () => housekeepingApi.complete(entry.id),
    ok: (u) => store.upsert(u),
    successMsg: (u) => `#${u.room_number}-xona toza deb belgilandi`,
    errorMsg: (e) => `Xato: ${parseApiError(e)}`
  })
  await run()
}
</script>

<template>
  <div class="page">
    <PageHeader title="Tozalash navbati" />

    <section v-if="store.error" class="error">{{ store.error }}</section>
    <section v-if="store.loading && !store.entries.length" class="empty card-paper">Navbat yuklanmoqda…</section>

    <template v-else>
      <div class="section-divider">Kutmoqda ({{ store.pending.length }})</div>
      <article v-if="!store.pending.length" class="empty card-paper">Kutayotgan xonalar yo‘q.</article>
      <div v-else class="grid">
        <article v-for="e in store.pending" :key="e.id" class="card-paper entry">
          <div class="head">
            <span class="room">#{{ e.room_number }}-xona</span>
            <StatusBadge :tone="e.status" />
          </div>
          <div class="meta">
            <span>{{ e.floor }}-qavat</span>
            <span class="text-muted text-caption">navbatga qo‘shildi {{ new Date(e.queued_at).toLocaleTimeString('uz-UZ') }}</span>
          </div>
          <div v-if="e.do_not_disturb" class="dnd-flag" title="Mehmon bezovta qilmang rejimini yoqgan">⚠ Bezovta qilmang</div>
          <div class="text-muted text-caption">Afzal vaqt: {{ prefLabels[e.cleaning_preference] || e.cleaning_preference }}<span v-if="e.cleaning_preference_note"> — “{{ e.cleaning_preference_note }}”</span></div>
          <Button v-if="canWork" variant="primary" size="sm" @click="startEntry(e)" :disabled="e.do_not_disturb">Tozalashni boshlash</Button>
        </article>
      </div>

      <div class="section-divider">Bajarilmoqda ({{ store.inProgress.length }})</div>
      <article v-if="!store.inProgress.length" class="empty card-paper">Hozircha bajarilayotgan tozalash yo‘q.</article>
      <div v-else class="grid">
        <article v-for="e in store.inProgress" :key="e.id" class="card-paper entry entry--working">
          <div class="head">
            <span class="room">#{{ e.room_number }}-xona</span>
            <StatusBadge :tone="e.status" />
          </div>
          <div class="meta">
            <span>{{ e.floor }}-qavat</span>
            <span v-if="e.started_at" class="text-muted text-caption">boshlandi {{ new Date(e.started_at).toLocaleTimeString('uz-UZ') }}</span>
          </div>
          <Button v-if="canWork" variant="success" size="sm" @click="completeEntry(e)">Toza deb belgilash</Button>
        </article>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }

.error {
  padding: 14px;
  background: color-mix(in srgb, var(--danger) 10%, transparent);
  color: var(--danger);
  border-radius: var(--radius-md);
}
.empty { padding: 32px; text-align: center; color: var(--muted-fg); }

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}

.entry {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: box-shadow var(--motion-fast) var(--motion-ease), transform var(--motion-fast) var(--motion-ease);
}
.entry:hover { box-shadow: var(--elev-2); transform: translateY(-1px); }
.entry--working { border-color: color-mix(in srgb, var(--primary) 40%, var(--border)); }

.head { display: flex; justify-content: space-between; align-items: center; }
.room { font-family: var(--font-display); font-weight: 600; font-size: var(--font-size-md); }
.meta { display: flex; justify-content: space-between; font-size: var(--font-size-xs); }
.dnd-flag {
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--warning, #f59e0b) 14%, transparent);
  color: var(--warning, #b45309);
  font-size: var(--font-size-xs);
  font-weight: 600;
}
</style>
