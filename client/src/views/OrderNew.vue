<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { receptionApi, type Guest, type Order, type OrderItem } from '@/api/reception'
import { menuApi, type MenuItem } from '@/api/menu'
import { useToastStore } from '@/stores/toast'
import { parseApiError } from '@/composables/useOptimistic'
import { Loader2, Minus, Plus } from 'lucide-vue-next'

const emit = defineEmits<{ success: [order: Order]; cancel: [] }>()
const toast = useToastStore()

const guests = ref<Guest[]>([])
const menu = ref<MenuItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const form = ref({ guest_id: '' })
const quantities = ref<Record<string, number>>({})
const submitting = ref(false)

onMounted(async () => {
  try {
    const [g, m] = await Promise.all([receptionApi.listGuests(), menuApi.list(true)])
    guests.value = g
    menu.value = m
  } catch (e: unknown) { error.value = parseApiError(e) }
  finally { loading.value = false }
})

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
  selectedItems.value.reduce((m, x) => Math.max(m, x.item.prep_minutes), 0)
)

function money(minor: number) { return (minor / 100).toLocaleString('uz-UZ') + " so'm" }

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
  if (!cleanItems.length) { error.value = 'Kamida bitta mahsulot tanlang.'; return }

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
  <form @submit.prevent="submit" class="space-y-5" novalidate>
    <div class="space-y-2">
      <Label>Faol mehmon</Label>
      <Select v-model="form.guest_id" :disabled="loading">
        <SelectTrigger>
          <SelectValue :placeholder="loading ? 'Yuklanmoqda…' : 'Mehmonni tanlang'" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem v-for="g in guests" :key="g.id" :value="g.id">
            {{ g.full_name }} — #{{ g.room_number }}-xona
          </SelectItem>
        </SelectContent>
      </Select>
    </div>

    <!-- Menu -->
    <div class="border rounded-lg p-3 max-h-80 overflow-y-auto space-y-4">
      <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Menyu</p>
      <div v-if="loading" class="text-sm text-muted-foreground">Yuklanmoqda…</div>
      <div v-else-if="!menu.length" class="text-sm text-muted-foreground">Mavjud menyu yo'q.</div>
      <template v-else>
        <div v-for="[cat, items] in menuByCategory" :key="cat" class="space-y-2">
          <p class="text-xs font-semibold text-muted-foreground capitalize">{{ cat }}</p>
          <div v-for="m in items" :key="m.id" class="flex items-center justify-between py-2 border-b border-dashed last:border-0">
            <div>
              <p class="text-sm font-medium">{{ m.name }}</p>
              <p class="text-xs text-muted-foreground">{{ money(m.price_minor_units) }} · {{ m.prep_minutes }} daq</p>
            </div>
            <div class="flex items-center gap-2">
              <Button variant="outline" size="icon-sm" type="button" :disabled="(quantities[m.id] ?? 0) === 0" @click="bump(m.id, -1)">
                <Minus class="w-3 h-3" />
              </Button>
              <span class="w-6 text-center text-sm font-semibold tabular-nums">{{ quantities[m.id] ?? 0 }}</span>
              <Button variant="outline" size="icon-sm" type="button" @click="bump(m.id, 1)">
                <Plus class="w-3 h-3" />
              </Button>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Summary -->
    <div class="space-y-2 border-t pt-3">
      <div class="flex justify-between text-sm"><span>Mahsulotlar</span><span class="tabular-nums">{{ selectedItems.length }}</span></div>
      <div class="flex justify-between text-sm"><span>Taxminiy tayyorlash</span><span class="tabular-nums">{{ estimatedPrepMinutes }} daq</span></div>
      <div class="flex justify-between font-semibold"><span>Jami</span><span class="tabular-nums">{{ money(totalMinor) }}</span></div>
    </div>

    <div v-if="error" class="rounded-md bg-destructive/10 text-destructive text-sm p-3" role="alert">{{ error }}</div>

    <div class="flex justify-end gap-2 pt-2">
      <Button variant="outline" type="button" :disabled="submitting" @click="emit('cancel')">Bekor</Button>
      <Button type="submit" :disabled="submitting || loading">
        <Loader2 v-if="submitting" class="w-4 h-4 mr-2 animate-spin" />
        Buyurtmani yuborish ({{ money(totalMinor) }})
      </Button>
    </div>
  </form>
</template>
