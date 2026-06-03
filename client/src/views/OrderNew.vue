<script setup lang="ts">
/**
 * Embeddable new-order form. Mounted inside a Modal from OrdersList.
 *
 * Items are picked from the kitchen menu (room-service owns it). Free-text
 * line items are no longer allowed — a typo on price would corrupt the bill.
 */
import { computed, onMounted, ref } from 'vue'
import Button from '@/components/Button.vue'
import { receptionApi, type Guest, type Order, type OrderItem } from '@/api/reception'
import { menuApi, type MenuItem } from '@/api/menu'
import { useToastStore } from '@/stores/toast'
import { parseApiError } from '@/composables/useOptimistic'

const emit = defineEmits<{ success: [order: Order]; cancel: [] }>()
const toast = useToastStore()

const guests = ref<Guest[]>([])
const menu = ref<MenuItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const form = ref({ guest_id: '' })
// Quantities keyed by menu item id. Zero = not in the order.
const quantities = ref<Record<string, number>>({})
const submitting = ref(false)

onMounted(async () => {
  try {
    const [g, m] = await Promise.all([
      receptionApi.listGuests(),
      menuApi.list(true)
    ])
    guests.value = g
    menu.value = m
  } catch (e: unknown) {
    error.value = parseApiError(e)
  } finally {
    loading.value = false
  }
})

const selectedGuest = computed(() =>
  guests.value.find((g) => g.id === form.value.guest_id) ?? null
)

const menuByCategory = computed(() => {
  const map = new Map<string, MenuItem[]>()
  for (const item of menu.value) {
    if (!map.has(item.category)) map.set(item.category, [])
    map.get(item.category)!.push(item)
  }
  return map
})

const selectedItems = computed(() =>
  menu.value
    .filter((m) => (quantities.value[m.id] ?? 0) > 0)
    .map((m) => ({ item: m, qty: quantities.value[m.id]! }))
)

const totalMinor = computed(() =>
  selectedItems.value.reduce((s, x) => s + x.item.price_minor_units * x.qty, 0)
)

const estimatedPrepMinutes = computed(() =>
  // The longest single-item prep dominates — kitchen cooks in parallel.
  selectedItems.value.reduce((m, x) => Math.max(m, x.item.prep_minutes), 0)
)

function money(minor: number) { return `$${(minor / 100).toFixed(2)}` }

function bump(id: string, delta: number) {
  const next = Math.max(0, Math.min(99, (quantities.value[id] ?? 0) + delta))
  quantities.value[id] = next
}

async function submit() {
  error.value = null
  if (!form.value.guest_id) { error.value = 'Mehmonni tanlang.'; return }
  const cleanItems: OrderItem[] = selectedItems.value.map((x) => ({
    name: x.item.name,
    qty: x.qty,
    price_minor_units: x.item.price_minor_units
  }))
  if (!cleanItems.length) {
    error.value = 'Kamida bitta mahsulot tanlang.'
    return
  }

  submitting.value = true
  try {
    const created = await receptionApi.createOrder({
      guest_id: form.value.guest_id,
      items: cleanItems
    })
    toast.success(`#${created.room_number}-xona uchun buyurtma qabul qilindi (${money(created.total_minor_units)})`)
    emit('success', created)
  } catch (e: unknown) { error.value = parseApiError(e) }
  finally { submitting.value = false }
}
</script>

<template>
  <form class="form" @submit.prevent="submit" novalidate>
    <label class="field">
      <span>Faol mehmon</span>
      <select v-model="form.guest_id" class="select" required :disabled="loading">
        <option value="" disabled>
          {{ loading ? 'Yuklanmoqda…' : guests.length ? 'Mehmonni tanlang' : 'Faol mehmonlar yo‘q' }}
        </option>
        <option v-for="g in guests" :key="g.id" :value="g.id">
          {{ g.full_name }} — #{{ g.room_number }}-xona ({{ g.floor }}-qavat)
        </option>
      </select>
      <span v-if="selectedGuest" class="hint">
        Telefon: {{ selectedGuest.phone }}
      </span>
    </label>

    <div class="menu-block">
      <div class="menu-head">Menyu</div>
      <div v-if="loading" class="hint">Menyu yuklanmoqda…</div>
      <div v-else-if="!menu.length" class="hint">Mavjud menyu yo‘q — menejerga ayting.</div>
      <template v-else>
        <div v-for="[cat, items] in menuByCategory" :key="cat" class="category">
          <div class="cat-name">{{ cat }}</div>
          <div v-for="m in items" :key="m.id" class="menu-row">
            <div class="name">
              <div class="title">{{ m.name }}</div>
              <div class="sub">{{ money(m.price_minor_units) }} · {{ m.prep_minutes }} daq</div>
            </div>
            <div class="qty">
              <button type="button" class="qty-btn" @click="bump(m.id, -1)" :disabled="(quantities[m.id] ?? 0) === 0">−</button>
              <span class="qty-val tabular">{{ quantities[m.id] ?? 0 }}</span>
              <button type="button" class="qty-btn" @click="bump(m.id, 1)">+</button>
            </div>
          </div>
        </div>
      </template>
    </div>

    <div class="summary">
      <div class="line"><span>Mahsulotlar</span><span class="tabular">{{ selectedItems.length }}</span></div>
      <div class="line"><span>Taxminiy tayyorlash</span><span class="tabular">{{ estimatedPrepMinutes }} daq</span></div>
      <div class="line total"><span>Jami</span><span class="tabular">{{ money(totalMinor) }}</span></div>
    </div>

    <div v-if="error" class="error" role="alert">{{ error }}</div>

    <div class="row-foot">
      <Button variant="ghost" size="md" type="button" :disabled="submitting" @click="emit('cancel')">Bekor qilish</Button>
      <Button type="submit" variant="primary" size="md" :loading="submitting || loading">
        {{ submitting ? 'Yuborilmoqda…' : `Buyurtmani yuborish (${money(totalMinor)})` }}
      </Button>
    </div>
  </form>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: 18px; }

.menu-block {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
  max-height: 360px;
  overflow-y: auto;
}
.menu-head {
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted-fg);
  font-weight: 600;
  margin-bottom: 8px;
}
.category + .category { margin-top: 14px; }
.cat-name {
  font-weight: 600;
  font-size: var(--font-size-xs);
  text-transform: capitalize;
  color: var(--muted-fg);
  margin-bottom: 6px;
}
.menu-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 4px;
  border-bottom: 1px dashed var(--border);
}
.menu-row:last-child { border-bottom: none; }
.name .title { font-weight: 500; }
.name .sub { font-size: var(--font-size-xs); color: var(--muted-fg); }
.qty { display: flex; align-items: center; gap: 8px; }
.qty-btn {
  width: 28px; height: 28px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--surface);
  cursor: pointer;
  font-size: 16px;
}
.qty-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.qty-val { min-width: 22px; text-align: center; font-weight: 600; }

.summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-top: 1px solid var(--border);
  padding-top: 10px;
}
.summary .line { display: flex; justify-content: space-between; font-size: var(--font-size-sm); }
.summary .total { font-weight: 700; font-size: var(--font-size-md); }

.error {
  padding: 11px 14px;
  background: color-mix(in srgb, var(--danger) 10%, transparent);
  color: var(--danger);
  border-radius: 10px;
  font-size: var(--font-size-sm);
}

.row-foot { display: flex; justify-content: flex-end; gap: 8px; padding-top: 4px; }
.tabular { font-variant-numeric: tabular-nums; }
.hint { font-size: var(--font-size-xs); color: var(--muted-fg); }
</style>
