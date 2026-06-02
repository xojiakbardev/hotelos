<script setup lang="ts">
/**
 * Embeddable new-order form. Mounted inside a Modal from OrdersList.
 */
import { computed, onMounted, ref } from 'vue'
import Button from '@/components/Button.vue'
import { receptionApi, type Guest, type Order, type OrderItem } from '@/api/reception'
import { useToastStore } from '@/stores/toast'
import { parseApiError } from '@/composables/useOptimistic'

const emit = defineEmits<{ success: [order: Order]; cancel: [] }>()
const toast = useToastStore()

interface ItemRow { name: string; qty: number; price_dollars: number }

const guests = ref<Guest[]>([])
const loadingGuests = ref(true)
const error = ref<string | null>(null)

const form = ref({ guest_id: '' })
const items = ref<ItemRow[]>([{ name: '', qty: 1, price_dollars: 0 }])
const submitting = ref(false)

onMounted(async () => {
  try { guests.value = await receptionApi.listGuests() }
  catch (e: unknown) { error.value = parseApiError(e) }
  finally { loadingGuests.value = false }
})

function addItem() { items.value.push({ name: '', qty: 1, price_dollars: 0 }) }
function removeItem(idx: number) { if (items.value.length > 1) items.value.splice(idx, 1) }

const selectedGuest = computed(() => guests.value.find((g) => g.id === form.value.guest_id) ?? null)

const totalMinor = computed(() =>
  items.value.reduce(
    (sum, i) => sum + Math.round((Number(i.qty) || 0) * (Number(i.price_dollars) || 0) * 100), 0
  )
)
function money(minor: number) { return `$${(minor / 100).toFixed(2)}` }

async function submit() {
  error.value = null
  if (!form.value.guest_id) { error.value = 'Mehmonni tanlang.'; return }
  const cleanItems: OrderItem[] = items.value
    .map((i) => ({
      name: i.name.trim(),
      qty: Number(i.qty),
      price_minor_units: Math.round(Number(i.price_dollars) * 100)
    }))
    .filter((i) => i.name && i.qty >= 1 && i.price_minor_units > 0)

  if (!cleanItems.length) {
    error.value = 'Kamida bitta mahsulot kerak: nomi, miqdori ≥ 1, narxi > 0.'
    return
  }

  submitting.value = true
  try {
    const created = await receptionApi.createOrder({ guest_id: form.value.guest_id, items: cleanItems })
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
      <select v-model="form.guest_id" class="select" required :disabled="loadingGuests">
        <option value="" disabled>
          {{ loadingGuests ? 'Yuklanmoqda…' : guests.length ? 'Mehmonni tanlang' : 'Faol mehmonlar yo‘q' }}
        </option>
        <option v-for="g in guests" :key="g.id" :value="g.id">
          {{ g.full_name }} — #{{ g.room_number }}-xona ({{ g.floor }}-qavat)
        </option>
      </select>
      <span v-if="selectedGuest" class="hint">
        Telefon: {{ selectedGuest.phone }} · tunlik narx {{ money(selectedGuest.nightly_rate_locked_minor_units) }}
      </span>
    </label>

    <div class="items-block">
      <div class="items-head">
        <span>Nomi</span>
        <span class="num">Miqdori</span>
        <span class="num">Narxi ($)</span>
        <span />
      </div>
      <div v-for="(i, idx) in items" :key="idx" class="item-row">
        <input v-model="i.name" class="input" type="text" placeholder="masalan, Espresso" maxlength="64" required />
        <input v-model.number="i.qty" class="input num" type="number" min="1" max="99" required />
        <input v-model.number="i.price_dollars" class="input num" type="number" min="0.01" step="0.50" required />
        <button
          type="button"
          class="remove"
          :disabled="items.length === 1"
          @click="removeItem(idx)"
        >−</button>
      </div>
      <Button type="button" variant="secondary" size="sm" @click="addItem">+ Yana mahsulot qo‘shish</Button>
      <div class="total-row">
        <span class="hint">Jami</span>
        <span class="total tabular">{{ money(totalMinor) }}</span>
      </div>
    </div>

    <div v-if="error" class="error" role="alert">{{ error }}</div>

    <div class="row-foot">
      <Button variant="ghost" size="md" type="button" :disabled="submitting" @click="emit('cancel')">Bekor qilish</Button>
      <Button type="submit" variant="primary" size="md" :loading="submitting || loadingGuests">
        {{ submitting ? 'Yuborilmoqda…' : `Buyurtmani yuborish (${money(totalMinor)})` }}
      </Button>
    </div>
  </form>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: 18px; }

.items-block { display: flex; flex-direction: column; gap: 8px; }

.items-head {
  display: grid;
  grid-template-columns: 1fr 80px 100px 36px;
  gap: 8px;
  font-size: var(--font-size-xs);
  color: var(--muted-fg);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
  padding: 0 4px;
}
.item-row { display: grid; grid-template-columns: 1fr 80px 100px 36px; gap: 8px; }
.input.num { text-align: right; }

.remove {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--danger);
  border-radius: 10px;
  font-size: 18px;
  font-weight: 600;
}
.remove:hover:enabled { background: color-mix(in srgb, var(--danger) 10%, transparent); }
.remove:disabled { opacity: 0.4; cursor: not-allowed; }

.total-row {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid var(--border);
  padding-top: 10px;
  margin-top: 4px;
}
.total { font-weight: 700; font-size: var(--font-size-lg); font-family: var(--font-display); color: var(--ink-900); }

.error {
  padding: 11px 14px;
  background: color-mix(in srgb, var(--danger) 10%, transparent);
  color: var(--danger);
  border-radius: 10px;
  font-size: var(--font-size-sm);
}

.row-foot { display: flex; justify-content: flex-end; gap: 8px; padding-top: 4px; }
.num { text-align: right; }
</style>
