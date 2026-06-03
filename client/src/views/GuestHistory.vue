<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import Button from '@/components/Button.vue'
import StatCard from '@/components/StatCard.vue'
import { receptionApi, type GuestHistory } from '@/api/reception'
import { parseApiError } from '@/composables/useOptimistic'

const route = useRoute()
const router = useRouter()

const history = ref<GuestHistory | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const phone = computed(() => String(route.params.phone || ''))

function money(minor: number) { return `$${(minor / 100).toFixed(2)}` }

async function load() {
  loading.value = true
  error.value = null
  try {
    history.value = await receptionApi.guestHistory(phone.value)
  } catch (e: unknown) {
    error.value = parseApiError(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(phone, load)
</script>

<template>
  <div class="page">
    <PageHeader :title="history ? `${history.full_name} — tarix` : 'Mehmon tarixi'">
      <template #actions>
        <Button variant="ghost" size="md" @click="router.back()">← Orqaga</Button>
      </template>
    </PageHeader>

    <section v-if="error" class="error">{{ error }}</section>
    <section v-if="loading" class="empty card-paper">Yuklanmoqda…</section>

    <template v-else-if="history">
      <section class="stats">
        <StatCard label="Telefon" :value="history.phone" hint="Mehmon kaliti" />
        <StatCard label="Jami tashriflar" :value="history.total_stays" :hint="history.repeat_visitor ? 'Qaytmas mehmon' : 'Yangi mehmon'" tone="primary" />
        <StatCard label="Jami tunlar" :value="history.total_nights" hint="Barcha tashriflar" />
        <StatCard label="Jami sarflangan" :value="money(history.total_spent_minor_units)" hint="Yakunlangan hisoblar" tone="success" />
      </section>

      <article class="card-paper table-wrap">
        <div class="section-header">Tashriflar tarixi</div>
        <table class="data">
          <thead>
            <tr>
              <th>Xona</th>
              <th>Kirish</th>
              <th>Chiqish</th>
              <th class="num">Tunlar</th>
              <th class="num">To‘lov</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in history.stays" :key="s.guest_id">
              <td>#{{ s.room_number }} <span class="text-muted">/ {{ s.floor }}-q</span></td>
              <td>{{ new Date(s.checked_in_at).toLocaleDateString('uz-UZ') }}</td>
              <td>{{ s.checked_out_at ? new Date(s.checked_out_at).toLocaleDateString('uz-UZ') : '—' }}</td>
              <td class="num tabular">{{ s.nights }}</td>
              <td class="num mono tabular">{{ s.total_minor_units !== null ? money(s.total_minor_units) : '—' }}</td>
              <td>
                <span v-if="s.checked_out_at" class="chip chip--ok">Yakunlangan</span>
                <span v-else class="chip chip--live">Hozir mehmonxonada</span>
              </td>
            </tr>
          </tbody>
        </table>
      </article>
    </template>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; }
.error { padding: 14px; background: color-mix(in srgb, var(--danger) 10%, transparent); color: var(--danger); border-radius: var(--radius-md); }
.empty { padding: 48px; text-align: center; color: var(--muted-fg); }

.table-wrap { padding: 0; overflow: hidden; }
.section-header { padding: 14px 18px; font-weight: 600; font-size: var(--font-size-sm); color: var(--muted-fg); text-transform: uppercase; letter-spacing: 0.05em; background: var(--bg-subtle); }
.data { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.data th, .data td { padding: 12px 18px; text-align: left; border-bottom: 1px solid var(--border); }
.data thead th { background: var(--bg-subtle); font-weight: 600; font-size: var(--font-size-xs); text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted-fg); }
.data tbody tr:last-child td { border-bottom: none; }
.data .num { text-align: right; }
.mono { font-family: var(--font-mono); }
.tabular { font-variant-numeric: tabular-nums; }

.chip { padding: 4px 10px; border-radius: var(--radius-full); font-size: var(--font-size-xs); font-weight: 500; }
.chip--ok { background: color-mix(in srgb, var(--success, #059669) 14%, transparent); color: var(--success, #059669); }
.chip--live { background: color-mix(in srgb, var(--primary) 14%, transparent); color: var(--primary); }
</style>
