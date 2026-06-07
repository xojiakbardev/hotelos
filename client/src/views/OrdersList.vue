<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import OrderNew from './OrderNew.vue'
import { receptionApi, type Order, type OrderStatus } from '@/api/reception'
import { menuApi, type MenuItem, type MenuItemPayload } from '@/api/menu'
import { useOrdersStore } from '@/stores/orders'
import { useWsStore } from '@/stores/ws'
import { useAuthStore } from '@/stores/auth'
import { parseApiError, useOptimistic } from '@/composables/useOptimistic'
import { ORDER_STATUS_UZ } from '@/lib/labels'
import { cn } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Plus,
  ChefHat,
  Truck,
  CheckCircle,
  Clock,
  Loader2,
  Pencil,
  Trash2,
} from 'lucide-vue-next'

const store = useOrdersStore()
const ws = useWsStore()
const auth = useAuthStore()

const newOpen = ref(false)

// Menu state
const menuItems = ref<MenuItem[]>([])
const menuLoading = ref(false)
const menuEditorOpen = ref(false)
const menuEditorMode = ref<'new' | 'edit'>('new')
const menuEditorItem = ref<MenuItem | null>(null)
const menuSaving = ref(false)
const menuDraft = ref({
  name: '',
  category: 'food',
  price_som: 0,
  prep_minutes: 10,
  is_available: true
})

const CATEGORY_UZ: Record<string, string> = {
  breakfast: 'Nonushta',
  food: 'Asosiy taom',
  snacks: 'Gazaklar',
  drinks: 'Ichimliklar',
  dessert: 'Shirinliklar',
  other: 'Boshqa'
}

onMounted(() => {
  store.load()
  loadMenu()
  loadHistory()
})

watch(
  () => ws.lastEvent,
  (env) => { if (env?.channel?.startsWith('orders.')) { store.load(); loadHistory() } }
)

const deliveredOrders = ref<Order[]>([])
const historyLoading = ref(false)

async function loadHistory() {
  historyLoading.value = true
  try { deliveredOrders.value = await receptionApi.listOrdersHistory() }
  catch { /* ignore */ }
  finally { historyLoading.value = false }
}

const canWork = computed(() => auth.role === 'manager' || auth.role === 'reception')
const isManager = computed(() => auth.role === 'manager')

const NEXT: Record<OrderStatus, OrderStatus | null> = {
  received: 'preparing',
  preparing: 'delivering',
  delivering: 'delivered',
  delivered: null
}
const NEXT_LABEL: Record<OrderStatus, string | null> = {
  received: 'Tayyorlash',
  preparing: 'Yetkazish',
  delivering: 'Yetkazildi',
  delivered: null
}

function money(minor: number) { return (minor / 100).toLocaleString('uz-UZ') + " so'm" }

function timeSince(iso: string) {
  const ms = Date.now() - new Date(iso).getTime()
  const min = Math.floor(ms / 60000)
  if (min < 1) return 'hozirgina'
  if (min < 60) return `${min} daq`
  return `${Math.floor(min / 60)}s ${min % 60}d`
}

function orderStatusVariant(s: OrderStatus): 'warning' | 'default' | 'success' | 'secondary' {
  if (s === 'received') return 'warning'
  if (s === 'preparing' || s === 'delivering') return 'default'
  if (s === 'delivered') return 'success'
  return 'secondary'
}

async function advance(order: Order) {
  const before = { ...order }
  const target = NEXT[order.status]
  if (!target) return
  const run = useOptimistic({
    apply: () => { order.status = target },
    revert: () => Object.assign(order, before),
    call: () => receptionApi.advanceOrder(order.id),
    ok: (u) => store.upsert(u),
    successMsg: (u) => `#${u.room_number} → ${ORDER_STATUS_UZ[u.status] ?? u.status}`,
    errorMsg: (e) => `Xato: ${parseApiError(e)}`
  })
  await run()
}

function onCreated() { newOpen.value = false; store.load(); loadHistory() }

async function loadMenu() {
  menuLoading.value = true
  try { menuItems.value = await menuApi.list(false) }
  finally { menuLoading.value = false }
}

function openMenuEditor(item: MenuItem | 'new') {
  if (item === 'new') {
    menuEditorMode.value = 'new'
    menuEditorItem.value = null
    menuDraft.value = { name: '', category: 'food', price_som: 0, prep_minutes: 10, is_available: true }
  } else {
    menuEditorMode.value = 'edit'
    menuEditorItem.value = item
    menuDraft.value = {
      name: item.name,
      category: item.category,
      price_som: item.price_minor_units / 100,
      prep_minutes: item.prep_minutes,
      is_available: item.is_available
    }
  }
  menuEditorOpen.value = true
}

async function saveMenu() {
  menuSaving.value = true
  try {
    const payload: MenuItemPayload = {
      name: menuDraft.value.name.trim(),
      category: menuDraft.value.category,
      price_minor_units: Math.round(menuDraft.value.price_som * 100),
      prep_minutes: menuDraft.value.prep_minutes,
      is_available: menuDraft.value.is_available
    }
    if (menuEditorMode.value === 'new') {
      const created = await menuApi.create(payload)
      menuItems.value = [created, ...menuItems.value]
    } else if (menuEditorItem.value) {
      const updated = await menuApi.update(menuEditorItem.value.id, payload)
      menuItems.value = menuItems.value.map(i => i.id === updated.id ? updated : i)
    }
    menuEditorOpen.value = false
  } catch (e) { alert(parseApiError(e)) }
  finally { menuSaving.value = false }
}

async function toggleAvail(item: MenuItem) {
  const target = !item.is_available
  item.is_available = target
  try { await menuApi.setAvailability(item.id, target) }
  catch { item.is_available = !target }
}

async function deleteMenuItem(item: MenuItem) {
  try { await menuApi.remove(item.id); menuItems.value = menuItems.value.filter(i => i.id !== item.id) }
  catch (e) { alert(parseApiError(e)) }
}
</script>

<template>
  <div class="space-y-6">
    <Tabs default-value="orders">
      <div class="flex items-center justify-between">
        <TabsList>
          <TabsTrigger value="orders">Buyurtmalar ({{ store.open.length }})</TabsTrigger>
          <TabsTrigger value="history">Tarix ({{ deliveredOrders.length }})</TabsTrigger>
          <TabsTrigger value="menu">Menyu ({{ menuItems.length }})</TabsTrigger>
        </TabsList>
        <div class="flex gap-2">
          <Button v-if="canWork" size="sm" @click="newOpen = true">
            <Plus class="w-4 h-4 mr-1" />
            Buyurtma
          </Button>
        </div>
      </div>

      <!-- ORDERS TAB -->
      <TabsContent value="orders" class="space-y-4">
        <!-- Status counts -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Card>
            <CardContent class="p-4 flex items-center gap-3">
              <div class="h-8 w-8 rounded-md bg-warning/10 grid place-items-center">
                <Clock class="w-4 h-4 text-amber-600" />
              </div>
              <div>
                <p class="text-lg font-bold">{{ store.orders.filter(o => o.status === 'received').length }}</p>
                <p class="text-xs text-muted-foreground">Qabul qilindi</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent class="p-4 flex items-center gap-3">
              <div class="h-8 w-8 rounded-md bg-primary/10 grid place-items-center">
                <ChefHat class="w-4 h-4 text-primary" />
              </div>
              <div>
                <p class="text-lg font-bold">{{ store.orders.filter(o => o.status === 'preparing').length }}</p>
                <p class="text-xs text-muted-foreground">Tayyorlanmoqda</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent class="p-4 flex items-center gap-3">
              <div class="h-8 w-8 rounded-md bg-primary/10 grid place-items-center">
                <Truck class="w-4 h-4 text-primary" />
              </div>
              <div>
                <p class="text-lg font-bold">{{ store.orders.filter(o => o.status === 'delivering').length }}</p>
                <p class="text-xs text-muted-foreground">Yetkazilmoqda</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent class="p-4 flex items-center gap-3">
              <div class="h-8 w-8 rounded-md bg-success/10 grid place-items-center">
                <CheckCircle class="w-4 h-4 text-green-600" />
              </div>
              <div>
                <p class="text-lg font-bold">{{ store.orders.filter(o => o.status === 'delivered').length }}</p>
                <p class="text-xs text-muted-foreground">Yetkazildi</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div v-if="store.error" class="rounded-md bg-destructive/10 text-destructive text-sm p-4">{{ store.error }}</div>
        <div v-if="store.loading && !store.orders.length" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card v-for="i in 4" :key="i">
            <CardContent class="p-4 space-y-3">
              <Skeleton class="h-5 w-24" />
              <Skeleton class="h-20 w-full" />
            </CardContent>
          </Card>
        </div>
        <div v-else-if="!store.orders.length" class="text-center py-8 text-muted-foreground">Ochiq buyurtmalar yo'q.</div>

        <!-- Kanban Board -->
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <!-- Yangi (received) -->
          <div class="space-y-3">
            <div class="flex items-center gap-2 pb-2 border-b border-amber-200 dark:border-amber-900">
              <Clock class="w-4 h-4 text-amber-600" />
              <span class="text-sm font-semibold">Yangi</span>
              <Badge variant="warning" class="text-[10px] ml-auto">{{ store.orders.filter(o => o.status === 'received').length }}</Badge>
            </div>
            <Card
              v-for="o in store.orders.filter(o => o.status === 'received')"
              :key="o.id"
              class="border-l-3 border-l-amber-400"
            >
              <CardContent class="p-3 space-y-2">
                <div class="flex items-center justify-between">
                  <span class="font-mono font-bold text-sm">#{{ o.room_number }}</span>
                  <span class="text-[10px] text-muted-foreground">{{ timeSince(o.received_at) }}</span>
                </div>
                <ul class="space-y-0.5">
                  <li v-for="item in o.items" :key="item.name" class="text-xs flex justify-between">
                    <span><span class="text-muted-foreground">{{ item.qty }}×</span> {{ item.name }}</span>
                    <span class="text-muted-foreground font-mono">{{ money(item.qty * item.price_minor_units) }}</span>
                  </li>
                </ul>
                <div class="flex items-center justify-between pt-2 border-t">
                  <span class="text-sm font-semibold">{{ money(o.total_minor_units) }}</span>
                  <Button v-if="canWork" size="xs" @click="advance(o)">
                    <ChefHat class="w-3 h-3 mr-1" />
                    Tayyorlash
                  </Button>
                </div>
              </CardContent>
            </Card>
            <p v-if="!store.orders.filter(o => o.status === 'received').length" class="text-xs text-muted-foreground text-center py-4">—</p>
          </div>

          <!-- Tayyorlanmoqda (preparing) -->
          <div class="space-y-3">
            <div class="flex items-center gap-2 pb-2 border-b border-blue-200 dark:border-blue-900">
              <ChefHat class="w-4 h-4 text-blue-600" />
              <span class="text-sm font-semibold">Tayyorlanmoqda</span>
              <Badge variant="default" class="text-[10px] ml-auto">{{ store.orders.filter(o => o.status === 'preparing').length }}</Badge>
            </div>
            <Card
              v-for="o in store.orders.filter(o => o.status === 'preparing')"
              :key="o.id"
              class="border-l-3 border-l-blue-500"
            >
              <CardContent class="p-3 space-y-2">
                <div class="flex items-center justify-between">
                  <span class="font-mono font-bold text-sm">#{{ o.room_number }}</span>
                  <span class="text-[10px] text-muted-foreground">{{ timeSince(o.preparing_at || o.received_at) }}</span>
                </div>
                <ul class="space-y-0.5">
                  <li v-for="item in o.items" :key="item.name" class="text-xs">
                    <span class="text-muted-foreground">{{ item.qty }}×</span> {{ item.name }}
                  </li>
                </ul>
                <Button v-if="canWork" size="xs" variant="outline" class="w-full" @click="advance(o)">
                  <Truck class="w-3 h-3 mr-1" />
                  Yetkazishga tayyor
                </Button>
              </CardContent>
            </Card>
            <p v-if="!store.orders.filter(o => o.status === 'preparing').length" class="text-xs text-muted-foreground text-center py-4">—</p>
          </div>

          <!-- Yetkazilmoqda (delivering) -->
          <div class="space-y-3">
            <div class="flex items-center gap-2 pb-2 border-b border-indigo-200 dark:border-indigo-900">
              <Truck class="w-4 h-4 text-indigo-600" />
              <span class="text-sm font-semibold">Yetkazilmoqda</span>
              <Badge variant="secondary" class="text-[10px] ml-auto">{{ store.orders.filter(o => o.status === 'delivering').length }}</Badge>
            </div>
            <Card
              v-for="o in store.orders.filter(o => o.status === 'delivering')"
              :key="o.id"
              class="border-l-3 border-l-indigo-500"
            >
              <CardContent class="p-3 space-y-2">
                <div class="flex items-center justify-between">
                  <span class="font-mono font-bold text-sm">#{{ o.room_number }}</span>
                  <span class="text-[10px] text-muted-foreground">{{ timeSince(o.delivering_at || o.received_at) }}</span>
                </div>
                <ul class="space-y-0.5">
                  <li v-for="item in o.items" :key="item.name" class="text-xs">
                    <span class="text-muted-foreground">{{ item.qty }}×</span> {{ item.name }}
                  </li>
                </ul>
                <Button v-if="canWork" size="xs" variant="success" class="w-full" @click="advance(o)">
                  <CheckCircle class="w-3 h-3 mr-1" />
                  Yetkazildi
                </Button>
              </CardContent>
            </Card>
            <p v-if="!store.orders.filter(o => o.status === 'delivering').length" class="text-xs text-muted-foreground text-center py-4">—</p>
          </div>

          <!-- Yetkazildi (delivered - today only) -->
          <div class="space-y-3">
            <div class="flex items-center gap-2 pb-2 border-b border-green-200 dark:border-green-900">
              <CheckCircle class="w-4 h-4 text-green-600" />
              <span class="text-sm font-semibold">Yetkazildi</span>
              <Badge variant="success" class="text-[10px] ml-auto">{{ store.delivered.length }}</Badge>
            </div>
            <Card
              v-for="o in store.delivered.slice(0, 5)"
              :key="o.id"
              class="border-l-3 border-l-green-500 opacity-75"
            >
              <CardContent class="p-3 space-y-1">
                <div class="flex items-center justify-between">
                  <span class="font-mono font-bold text-sm">#{{ o.room_number }}</span>
                  <span class="text-[10px] text-muted-foreground">{{ o.delivered_at ? timeSince(o.delivered_at) : '' }}</span>
                </div>
                <p class="text-xs text-muted-foreground">{{ o.items.map(i => `${i.qty}× ${i.name}`).join(', ') }}</p>
                <p class="text-xs font-semibold">{{ money(o.total_minor_units) }}</p>
              </CardContent>
            </Card>
            <p v-if="!store.delivered.length" class="text-xs text-muted-foreground text-center py-4">—</p>
          </div>
        </div>
      </TabsContent>

      <!-- HISTORY TAB -->
      <TabsContent value="history">
        <div v-if="historyLoading" class="text-center py-8 text-muted-foreground">Yuklanmoqda...</div>
        <div v-else-if="!deliveredOrders.length" class="text-center py-8 text-muted-foreground">Yetkazilgan buyurtmalar yo'q.</div>
        <Card v-else>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Xona</TableHead>
                <TableHead>Taomlar</TableHead>
                <TableHead class="text-right">Jami</TableHead>
                <TableHead>Yetkazildi</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="o in deliveredOrders" :key="o.id">
                <TableCell class="font-mono">#{{ o.room_number }}</TableCell>
                <TableCell class="text-sm">{{ o.items.map(i => `${i.name}×${i.qty}`).join(', ') }}</TableCell>
                <TableCell class="text-right font-mono tabular-nums">{{ money(o.total_minor_units) }}</TableCell>
                <TableCell class="text-muted-foreground">{{ o.delivered_at ? new Date(o.delivered_at).toLocaleString('uz-UZ') : '—' }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </Card>
      </TabsContent>

      <!-- MENU TAB -->
      <TabsContent value="menu">
        <div class="flex justify-end mb-4">
          <Button v-if="isManager" size="sm" @click="openMenuEditor('new')">
            <Plus class="w-4 h-4 mr-1" />
            Mahsulot
          </Button>
        </div>
        <div v-if="menuLoading" class="text-center py-8 text-muted-foreground">Yuklanmoqda…</div>
        <div v-else-if="!menuItems.length" class="text-center py-8 text-muted-foreground">Menyu bo'sh. Mahsulot qo'shing.</div>
        <Card v-else>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nomi</TableHead>
                <TableHead>Kategoriya</TableHead>
                <TableHead class="text-right">Narx</TableHead>
                <TableHead class="text-right">Vaqt</TableHead>
                <TableHead>Holat</TableHead>
                <TableHead v-if="isManager" class="text-right">Harakat</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="item in menuItems" :key="item.id" :class="{ 'opacity-50': !item.is_available }">
                <TableCell class="font-medium">{{ item.name }}</TableCell>
                <TableCell class="text-muted-foreground">{{ CATEGORY_UZ[item.category] || item.category }}</TableCell>
                <TableCell class="text-right font-mono tabular-nums">{{ money(item.price_minor_units) }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ item.prep_minutes }} daq</TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="xs"
                    :class="item.is_available ? 'text-green-600' : 'text-muted-foreground'"
                    @click="toggleAvail(item)"
                  >
                    {{ item.is_available ? 'Mavjud' : "O'chiq" }}
                  </Button>
                </TableCell>
                <TableCell v-if="isManager" class="text-right">
                  <div class="flex justify-end gap-1">
                    <Button variant="ghost" size="icon-sm" @click="openMenuEditor(item)">
                      <Pencil class="w-3.5 h-3.5" />
                    </Button>
                    <Button variant="ghost" size="icon-sm" class="text-destructive" @click="deleteMenuItem(item)">
                      <Trash2 class="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </Card>
      </TabsContent>
    </Tabs>

    <!-- New Order Dialog -->
    <Dialog :open="newOpen" @update:open="newOpen = $event">
      <DialogContent class="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Yangi buyurtma</DialogTitle>
        </DialogHeader>
        <OrderNew @cancel="newOpen = false" @success="onCreated" />
      </DialogContent>
    </Dialog>

    <!-- Menu Editor Dialog -->
    <Dialog :open="menuEditorOpen" @update:open="menuEditorOpen = $event">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{{ menuEditorMode === 'new' ? 'Yangi mahsulot' : 'Tahrirlash' }}</DialogTitle>
        </DialogHeader>
        <form @submit.prevent="saveMenu" class="space-y-4">
          <div class="space-y-2">
            <Label>Nomi</Label>
            <Input v-model="menuDraft.name" required maxlength="64" />
          </div>
          <div class="space-y-2">
            <Label>Kategoriya</Label>
            <Select v-model="menuDraft.category">
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="(label, key) in CATEGORY_UZ" :key="key" :value="key">{{ label }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label>Narx (so'm)</Label>
              <Input v-model.number="menuDraft.price_som" type="number" min="0" required />
            </div>
            <div class="space-y-2">
              <Label>Tayyorlash (daq)</Label>
              <Input v-model.number="menuDraft.prep_minutes" type="number" min="1" max="240" required />
            </div>
          </div>
          <div class="flex items-center gap-2">
            <input id="menu-avail" v-model="menuDraft.is_available" type="checkbox" class="rounded border-input" />
            <Label for="menu-avail">Hozirda mavjud</Label>
          </div>
          <DialogFooter>
            <Button variant="outline" type="button" :disabled="menuSaving" @click="menuEditorOpen = false">Bekor</Button>
            <Button type="submit" :disabled="menuSaving">
              <Loader2 v-if="menuSaving" class="w-4 h-4 mr-2 animate-spin" />
              Saqlash
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  </div>
</template>
