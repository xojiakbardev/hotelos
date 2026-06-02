<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import Button from '@/components/Button.vue'
import StatCard from '@/components/StatCard.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import Modal from '@/components/Modal.vue'
import OrderNew from './OrderNew.vue'
import { receptionApi, type Order, type OrderStatus } from '@/api/reception'
import { useOrdersStore } from '@/stores/orders'
import { useWsStore } from '@/stores/ws'
import { useAuthStore } from '@/stores/auth'
import { parseApiError, useOptimistic } from '@/composables/useOptimistic'
import { ORDER_STATUS_UZ } from '@/lib/labels'

const store = useOrdersStore()
const ws = useWsStore()
const auth = useAuthStore()

const newOpen = ref(false)

onMounted(() => store.load())

watch(
  () => ws.lastEvent,
  (env) => { if (env?.channel?.startsWith('orders.')) store.load() }
)

const canWork = computed(() => auth.role === 'manager' || auth.role === 'reception')

const NEXT: Record<OrderStatus, OrderStatus | null> = {
  received: 'preparing',
  preparing: 'delivering',
  delivering: 'delivered',
  delivered: null
}
const NEXT_LABEL: Record<OrderStatus, string | null> = {
  received: 'Tayyorlashni boshlash',
  preparing: 'Yetkazib berishga jo‘natish',
  delivering: 'Yetkazildi deb belgilash',
  delivered: null
}

const counts = computed(() => {
  const by = (s: OrderStatus) => store.orders.filter((o) => o.status === s).length
  return { received: by('received'), preparing: by('preparing'), delivering: by('delivering'), delivered: by('delivered') }
})

function money(minor: number) { return `$${(minor / 100).toFixed(2)}` }

async function advance(order: Order) {
  const before = { ...order }
  const target = NEXT[order.status]
  if (!target) return
  const run = useOptimistic({
    apply: () => { order.status = target },
    revert: () => Object.assign(order, before),
    call: () => receptionApi.advanceOrder(order.id),
    ok: (u) => store.upsert(u),
    successMsg: (u) => `#${u.room_number}-xona buyurtmasi → ${ORDER_STATUS_UZ[u.status] ?? u.status}`,
    errorMsg: (e) => `Xato: ${parseApiError(e)}`
  })
  await run()
}

function onCreated() {
  newOpen.value = false
  store.load()
}
</script>

<template>
  <div class="page">
    <PageHeader title="Xona xizmati">
      <template #actions>
        <Button v-if="canWork" variant="primary" size="md" @click="newOpen = true">Yangi buyurtma</Button>
      </template>
    </PageHeader>

    <section class="stats">
      <StatCard label="Qabul qilindi" :value="counts.received" hint="Kutmoqda" tone="warn" />
      <StatCard label="Tayyorlanmoqda" :value="counts.preparing" hint="Oshxonada" tone="primary" />
      <StatCard label="Yetkazilmoqda" :value="counts.delivering" hint="Yo‘lda" tone="primary" />
      <StatCard label="Yetkazildi" :value="counts.delivered" hint="Yakunlandi" tone="success" />
    </section>

    <section v-if="store.error" class="error">{{ store.error }}</section>
    <section v-if="store.loading && !store.orders.length" class="empty card-paper">Buyurtmalar yuklanmoqda…</section>

    <template v-else>
      <div class="section-divider">Ochiq buyurtmalar ({{ store.open.length }})</div>
      <article v-if="!store.open.length" class="empty card-paper">Ochiq buyurtmalar yo‘q.</article>
      <div v-else class="grid">
        <article
          v-for="o in store.open"
          :key="o.id"
          :class="['card-paper', 'order', `order--${o.status}`]"
        >
          <header class="order-head">
            <span class="room">#{{ o.room_number }} <span class="text-muted">/ {{ o.floor }}-qavat</span></span>
            <StatusBadge :tone="o.status" />
          </header>
          <ul class="items">
            <li v-for="(i, idx) in o.items" :key="idx">
              <span class="qty text-muted tabular">{{ i.qty }}×</span>
              <span class="name">{{ i.name }}</span>
              <span class="price text-muted tabular">{{ money(i.qty * i.price_minor_units) }}</span>
            </li>
          </ul>
          <footer class="order-foot">
            <span class="total tabular">Jami {{ money(o.total_minor_units) }}</span>
            <Button
              v-if="canWork && NEXT_LABEL[o.status]"
              variant="primary"
              size="sm"
              @click="advance(o)"
            >{{ NEXT_LABEL[o.status] }}</Button>
          </footer>
        </article>
      </div>
    </template>

    <Modal :open="newOpen" title="Yangi buyurtma" size="lg" @close="newOpen = false">
      <OrderNew @cancel="newOpen = false" @success="onCreated" />
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

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.order {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: box-shadow var(--motion-fast) var(--motion-ease), transform var(--motion-fast) var(--motion-ease);
}
.order:hover { box-shadow: var(--elev-2); transform: translateY(-1px); }
.order--received   { border-left: 3px solid var(--status-dirty); }
.order--preparing  { border-left: 3px solid var(--status-cleaning); }
.order--delivering { border-left: 3px solid var(--primary); }
.order--delivered  { opacity: 0.7; }

.order-head { display: flex; justify-content: space-between; align-items: center; }
.room { font-family: var(--font-display); font-weight: 600; font-size: var(--font-size-md); }

.items { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.items li { display: grid; grid-template-columns: auto 1fr auto; gap: 8px; font-size: var(--font-size-sm); }

.order-foot { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border); padding-top: 10px; }
.total { font-weight: 600; font-family: var(--font-display); color: var(--ink-800); }
</style>
