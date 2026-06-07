<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { useGuestPortalStore } from '@/stores/guest-portal'
import { useAuthStore } from '@/stores/auth'
import { useWsStore } from '@/stores/ws'
import { guestPortalApi, type MenuItem, type GuestOrderItem } from '@/api/guest-portal'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Separator } from '@/components/ui/separator'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import {
  UtensilsCrossed,
  Wrench,
  Sparkles,
  User,
  Plus,
  Minus,
  X,
  ShoppingCart,
  ArrowLeft,
  Loader2,
  KeyRound,
} from 'lucide-vue-next'

const store = useGuestPortalStore()
const auth = useAuthStore()
const ws = useWsStore()

// Password modal
const showPwModal = ref(false)
const pwCurrent = ref('')
const pwNew = ref('')
const pwConfirm = ref('')
const pwLoading = ref(false)
const pwError = ref('')

onMounted(() => {
  if (auth.mustChangePassword) showPwModal.value = true
  store.fetchDashboard()
})

watch(
  () => ws.lastEvent,
  (env) => {
    const ch = env?.channel ?? ''
    if (ch.startsWith('orders.') || ch.startsWith('maintenance.') || ch.startsWith('rooms.cleaning') || ch === 'rooms.cleaned') {
      store.fetchDashboard()
    }
  }
)

async function changePassword() {
  pwError.value = ''
  if (pwNew.value.length < 4) { pwError.value = 'Kamida 4 belgi'; return }
  if (pwNew.value !== pwConfirm.value) { pwError.value = 'Parollar mos kelmaydi'; return }
  pwLoading.value = true
  try {
    await auth.changePassword(pwCurrent.value, pwNew.value)
    showPwModal.value = false
  } catch (e: any) {
    pwError.value = e?.response?.data?.detail || 'Xatolik'
  } finally { pwLoading.value = false }
}

// Menu + order
const menuItems = ref<MenuItem[]>([])
const menuLoading = ref(false)
const orderStep = ref<'idle' | 'menu' | 'cart' | 'confirm'>('idle')
const cart = ref<Map<string, GuestOrderItem & { id: string }>>(new Map())
const submittingOrder = ref(false)

// Maintenance
const showMaintenanceForm = ref(false)
const maintenanceDesc = ref('')

// Cleaning
const showCleaningForm = ref(false)
const cleaningPriority = ref('normal')
const cleaningTime = ref('afternoon')
const cleaningNote = ref('')

const categories = computed(() => [...new Set(menuItems.value.map(i => i.category))].sort())
const selectedCategory = ref<string | null>(null)
const filteredMenu = computed(() => {
  if (!selectedCategory.value) return menuItems.value
  return menuItems.value.filter(i => i.category === selectedCategory.value)
})
const cartItems = computed(() => [...cart.value.values()])
const cartTotal = computed(() => cartItems.value.reduce((s, i) => s + i.price_minor_units * i.qty, 0))
const totalOrdersCost = computed(() => store.orders.reduce((s, o) => s + o.total_minor_units, 0))

const CATEGORY_UZ: Record<string, string> = { drinks: 'Ichimliklar', food: 'Ovqatlar', dessert: 'Shirinliklar', snacks: 'Gazaklar', other: 'Boshqa' }

// Cleaning preference
const cleaningPref = ref('afternoon')

async function updatePref(val: string) {
  cleaningPref.value = val
  try {
    await guestPortalApi.updateCleaningPreference(val)
  } catch { /* ignore */ }
}

function money(minor: number) { return (minor / 100).toLocaleString('uz-UZ') + " so'm" }

function statusVariant(s: string): 'default' | 'success' | 'warning' | 'secondary' {
  if (['delivered', 'resolved', 'completed'].includes(s)) return 'success'
  if (['preparing', 'delivering', 'assigned', 'in_progress'].includes(s)) return 'default'
  return 'secondary'
}
function statusLabel(s: string): string {
  const m: Record<string, string> = { received: 'Qabul qilindi', preparing: 'Tayyorlanmoqda', delivering: 'Yetkazilmoqda', delivered: 'Yetkazildi', reported: 'Xabar qilindi', assigned: 'Tayinlandi', resolved: 'Hal qilindi', pending: 'Kutilmoqda', in_progress: 'Bajarilmoqda', completed: 'Bajarildi' }
  return m[s] || s
}

async function startOrder() {
  orderStep.value = 'menu'
  cart.value = new Map()
  if (!menuItems.value.length) {
    menuLoading.value = true
    try { menuItems.value = await guestPortalApi.menu() } catch {}
    finally { menuLoading.value = false }
  }
  selectedCategory.value = categories.value[0] || null
}

function addToCart(item: MenuItem) {
  const ex = cart.value.get(item.id)
  if (ex) { ex.qty++ } else {
    cart.value.set(item.id, { id: item.id, menu_item_id: item.id, name: item.name, qty: 1, price_minor_units: item.price_minor_units })
  }
  cart.value = new Map(cart.value)
}
function changeQty(id: string, delta: number) {
  const item = cart.value.get(id)
  if (!item) return
  item.qty += delta
  if (item.qty <= 0) cart.value.delete(id)
  cart.value = new Map(cart.value)
}
function removeFromCart(id: string) { cart.value.delete(id); cart.value = new Map(cart.value) }

async function submitOrder() {
  submittingOrder.value = true
  try { await store.submitOrder(cartItems.value); orderStep.value = 'idle'; cart.value = new Map() }
  finally { submittingOrder.value = false }
}

async function submitMaintenance() {
  if (maintenanceDesc.value.length < 5) return
  await store.submitMaintenance(maintenanceDesc.value)
  showMaintenanceForm.value = false
  maintenanceDesc.value = ''
}

async function submitCleaning() {
  await store.submitCleaning({ priority: cleaningPriority.value, preferred_time: cleaningTime.value, note: cleaningNote.value || undefined })
  showCleaningForm.value = false
  cleaningNote.value = ''
}
</script>

<template>
  <div class="space-y-6">
    <!-- Loading -->
    <div v-if="store.loading" class="space-y-4">
      <Skeleton class="h-10 w-full rounded-md" />
      <Skeleton class="h-32 w-full rounded-lg" />
      <Skeleton class="h-32 w-full rounded-lg" />
    </div>

    <template v-else>
      <div v-if="store.error" class="rounded-md bg-destructive/10 text-destructive text-sm p-3">{{ store.error }}</div>

      <Tabs default-value="orders">
        <TabsList class="w-full">
          <TabsTrigger value="orders" class="flex-1 gap-1.5">
            <UtensilsCrossed class="w-4 h-4" />
            Ovqat
          </TabsTrigger>
          <TabsTrigger value="maintenance" class="flex-1 gap-1.5">
            <Wrench class="w-4 h-4" />
            Texnik
          </TabsTrigger>
          <TabsTrigger value="cleaning" class="flex-1 gap-1.5">
            <Sparkles class="w-4 h-4" />
            Tozalash
          </TabsTrigger>
          <TabsTrigger value="profile" class="flex-1 gap-1.5">
            <User class="w-4 h-4" />
            Profil
          </TabsTrigger>
        </TabsList>

        <!-- ORDERS -->
        <TabsContent value="orders" class="space-y-4">
          <!-- Idle -->
          <template v-if="orderStep === 'idle'">
            <Button class="w-full" @click="startOrder">
              <Plus class="w-4 h-4 mr-2" />
              Buyurtma berish
            </Button>
            <div v-if="!store.orders.length" class="text-center py-8 text-muted-foreground text-sm">Hali buyurtmalar yo'q</div>
            <Card v-for="order in store.orders" :key="order.id">
              <CardContent class="p-4 space-y-3">
                <div class="flex items-center justify-between">
                  <Badge :variant="statusVariant(order.status)">{{ statusLabel(order.status) }}</Badge>
                  <span class="font-semibold tabular-nums">{{ money(order.total_minor_units) }}</span>
                </div>
                <!-- Progress pipeline -->
                <div class="flex items-center gap-1">
                  <div v-for="(step, idx) in ['received','preparing','delivering','delivered']" :key="step" class="flex items-center gap-1 flex-1">
                    <div
                      class="h-1.5 flex-1 rounded-full transition-all"
                      :class="
                        ['received','preparing','delivering','delivered'].indexOf(order.status) >= idx
                          ? 'bg-primary'
                          : 'bg-muted'
                      "
                    />
                  </div>
                </div>
                <div class="flex justify-between text-[10px] text-muted-foreground">
                  <span>Qabul</span>
                  <span>Tayyorlanmoqda</span>
                  <span>Yetkazilmoqda</span>
                  <span>Tayyor</span>
                </div>
                <div class="flex flex-wrap gap-1">
                  <Badge v-for="item in order.items" :key="item.name" variant="secondary" class="text-xs">{{ item.name }} ×{{ item.qty }}</Badge>
                </div>
              </CardContent>
            </Card>
          </template>

          <!-- Menu -->
          <template v-if="orderStep === 'menu'">
            <div class="flex items-center justify-between">
              <h3 class="font-semibold">Menyu</h3>
              <Button variant="ghost" size="sm" @click="orderStep = 'idle'"><X class="w-4 h-4 mr-1" />Bekor</Button>
            </div>
            <div v-if="menuLoading" class="text-center py-6 text-muted-foreground">Yuklanmoqda...</div>
            <template v-else-if="menuItems.length">
              <div class="flex gap-2 flex-wrap">
                <Button v-for="cat in categories" :key="cat" :variant="selectedCategory === cat ? 'default' : 'outline'" size="xs" @click="selectedCategory = cat">
                  {{ CATEGORY_UZ[cat] || cat }}
                </Button>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <Card v-for="item in filteredMenu" :key="item.id" class="cursor-pointer hover:border-primary/50 transition-colors" @click="addToCart(item)">
                  <CardContent class="p-3">
                    <p class="text-sm font-medium">{{ item.name }}</p>
                    <div class="flex justify-between text-xs text-muted-foreground mt-1">
                      <span class="text-green-600 font-semibold">{{ money(item.price_minor_units) }}</span>
                      <span>~{{ item.prep_minutes }} daq</span>
                    </div>
                  </CardContent>
                </Card>
              </div>
              <div v-if="cartItems.length" class="sticky bottom-0 bg-card border rounded-lg p-3 flex items-center justify-between shadow-md">
                <span class="text-sm font-semibold">{{ cartItems.reduce((s, i) => s + i.qty, 0) }} ta · {{ money(cartTotal) }}</span>
                <Button size="sm" @click="orderStep = 'cart'"><ShoppingCart class="w-4 h-4 mr-1" />Savat</Button>
              </div>
            </template>
            <div v-else class="text-center py-6 text-muted-foreground text-sm">Menyu bo'sh</div>
          </template>

          <!-- Cart -->
          <template v-if="orderStep === 'cart'">
            <div class="flex items-center justify-between">
              <h3 class="font-semibold">Savat</h3>
              <Button variant="ghost" size="sm" @click="orderStep = 'menu'"><ArrowLeft class="w-4 h-4 mr-1" />Menyu</Button>
            </div>
            <div v-if="!cartItems.length" class="text-center py-6 text-muted-foreground">Savat bo'sh</div>
            <div v-else class="space-y-3">
              <Card v-for="item in cartItems" :key="item.id">
                <CardContent class="p-3 flex items-center justify-between">
                  <div>
                    <p class="text-sm font-medium">{{ item.name }}</p>
                    <p class="text-xs text-muted-foreground">{{ money(item.price_minor_units) }}</p>
                  </div>
                  <div class="flex items-center gap-2">
                    <Button variant="outline" size="icon-sm" @click="changeQty(item.id, -1)"><Minus class="w-3 h-3" /></Button>
                    <span class="text-sm font-bold w-5 text-center">{{ item.qty }}</span>
                    <Button variant="outline" size="icon-sm" @click="changeQty(item.id, 1)"><Plus class="w-3 h-3" /></Button>
                    <Button variant="ghost" size="icon-sm" class="text-destructive" @click="removeFromCart(item.id)"><X class="w-3 h-3" /></Button>
                  </div>
                </CardContent>
              </Card>
              <Separator />
              <div class="flex justify-between font-semibold text-lg">
                <span>Jami:</span>
                <span class="text-primary tabular-nums">{{ money(cartTotal) }}</span>
              </div>
              <Button class="w-full" @click="orderStep = 'confirm'">Tasdiqlash →</Button>
            </div>
          </template>

          <!-- Confirm -->
          <template v-if="orderStep === 'confirm'">
            <div class="flex items-center justify-between">
              <h3 class="font-semibold">Tasdiqlash</h3>
              <Button variant="ghost" size="sm" @click="orderStep = 'cart'"><ArrowLeft class="w-4 h-4 mr-1" />Orqaga</Button>
            </div>
            <Card>
              <CardContent class="p-4 space-y-3">
                <p class="text-sm text-muted-foreground">Buyurtmangiz xona xizmatiga yuboriladi.</p>
                <div class="space-y-2">
                  <div v-for="item in cartItems" :key="item.id" class="flex justify-between text-sm">
                    <span>{{ item.name }} × {{ item.qty }}</span>
                    <span class="font-mono tabular-nums">{{ money(item.price_minor_units * item.qty) }}</span>
                  </div>
                </div>
                <Separator />
                <div class="flex justify-between font-bold">
                  <span>Jami:</span>
                  <span>{{ money(cartTotal) }}</span>
                </div>
                <Button class="w-full" :disabled="submittingOrder" @click="submitOrder">
                  <Loader2 v-if="submittingOrder" class="w-4 h-4 mr-2 animate-spin" />
                  {{ submittingOrder ? 'Yuborilmoqda...' : 'Buyurtma berish' }}
                </Button>
              </CardContent>
            </Card>
          </template>
        </TabsContent>

        <!-- MAINTENANCE -->
        <TabsContent value="maintenance" class="space-y-4">
          <Button v-if="!showMaintenanceForm" class="w-full" @click="showMaintenanceForm = true">
            <Plus class="w-4 h-4 mr-2" />
            Muammo xabar qilish
          </Button>
          <Card v-if="showMaintenanceForm">
            <CardContent class="p-4 space-y-3">
              <p class="text-sm font-semibold">Texnik muammo</p>
              <Textarea v-model="maintenanceDesc" placeholder="Muammoni tasvirlang (kamida 5 belgi)" class="min-h-[80px]" />
              <div class="flex gap-2">
                <Button :disabled="maintenanceDesc.length < 5" @click="submitMaintenance">Yuborish</Button>
                <Button variant="outline" @click="showMaintenanceForm = false">Bekor</Button>
              </div>
            </CardContent>
          </Card>
          <div v-if="!store.maintenanceRequests.length" class="text-center py-8 text-muted-foreground text-sm">Texnik so'rovlar yo'q</div>
          <Card v-for="req in store.maintenanceRequests" :key="req.id">
            <CardContent class="p-4 space-y-2">
              <Badge :variant="statusVariant(req.status)">{{ statusLabel(req.status) }}</Badge>
              <p class="text-sm">{{ req.description }}</p>
            </CardContent>
          </Card>
        </TabsContent>

        <!-- CLEANING -->
        <TabsContent value="cleaning" class="space-y-4">
          <Button v-if="!showCleaningForm" class="w-full" @click="showCleaningForm = true">
            <Plus class="w-4 h-4 mr-2" />
            Tozalash so'rash
          </Button>
          <Card v-if="showCleaningForm">
            <CardContent class="p-4 space-y-3">
              <p class="text-sm font-semibold">Tozalash so'rovi</p>
              <div class="space-y-2">
                <Label>Muhimlik</Label>
                <Select v-model="cleaningPriority">
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Past</SelectItem>
                    <SelectItem value="normal">O'rta</SelectItem>
                    <SelectItem value="high">Yuqori</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div class="space-y-2">
                <Label>Vaqt</Label>
                <Select v-model="cleaningTime">
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="morning">Ertalab (08-12)</SelectItem>
                    <SelectItem value="afternoon">Tushlik (12-17)</SelectItem>
                    <SelectItem value="evening">Kechqurun (17-21)</SelectItem>
                    <SelectItem value="now">Hozir</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Textarea v-model="cleaningNote" placeholder="Izoh (ixtiyoriy)" />
              <div class="flex gap-2">
                <Button @click="submitCleaning">Yuborish</Button>
                <Button variant="outline" @click="showCleaningForm = false">Bekor</Button>
              </div>
            </CardContent>
          </Card>
          <div v-if="!store.cleaningRequests.length" class="text-center py-8 text-muted-foreground text-sm">Tozalash so'rovlari yo'q</div>
          <Card v-for="cr in store.cleaningRequests" :key="cr.id">
            <CardContent class="p-4 space-y-1">
              <div class="flex items-center gap-2">
                <Badge :variant="statusVariant(cr.status)">{{ statusLabel(cr.status) }}</Badge>
                <span class="text-xs text-muted-foreground">{{ cr.preferred_time }}</span>
              </div>
              <p v-if="cr.note" class="text-sm text-muted-foreground">{{ cr.note }}</p>
            </CardContent>
          </Card>
        </TabsContent>

        <!-- PROFILE -->
        <TabsContent value="profile" class="space-y-4">
          <Card>
            <CardContent class="p-5 space-y-4">
              <div class="flex items-center gap-4">
                <Avatar class="h-12 w-12">
                  <AvatarFallback class="bg-primary text-primary-foreground text-lg font-bold">
                    {{ store.guestName.slice(0, 1).toUpperCase() }}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <p class="font-semibold text-lg">{{ store.guestName }}</p>
                  <p class="text-sm text-muted-foreground">Xona #{{ store.roomNumber }} · {{ store.floor }}-qavat</p>
                </div>
              </div>
              <Separator />

              <!-- Cleaning preference -->
              <div class="space-y-2">
                <p class="text-xs font-semibold uppercase text-muted-foreground">Tozalash vaqti</p>
                <Select
                  :model-value="cleaningPref"
                  @update:model-value="updatePref"
                >
                  <SelectTrigger class="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="morning">Ertalab (08:00–12:00)</SelectItem>
                    <SelectItem value="afternoon">Tushdan keyin (12:00–17:00)</SelectItem>
                    <SelectItem value="evening">Kechqurun (17:00–21:00)</SelectItem>
                    <SelectItem value="custom">Maxsus vaqt</SelectItem>
                  </SelectContent>
                </Select>
                <p class="text-xs text-muted-foreground">Xonangiz qachon tozalanishini tanlang</p>
              </div>

              <Separator />
              <div class="space-y-2">
                <p class="text-xs font-semibold uppercase text-muted-foreground">Hisob-kitob</p>
                <div class="flex justify-between text-sm">
                  <span>Buyurtmalar ({{ store.orders.length }} ta)</span>
                  <span class="font-semibold tabular-nums">{{ money(totalOrdersCost) }}</span>
                </div>
              </div>
              <Separator />
              <Button variant="outline" class="w-full" @click="showPwModal = true">
                <KeyRound class="w-4 h-4 mr-2" />
                Parolni o'zgartirish
              </Button>
            </CardContent>
          </Card>

          <!-- Order history -->
          <div v-if="store.orders.length" class="space-y-3">
            <p class="text-xs font-semibold uppercase text-muted-foreground">Buyurtmalar tarixi</p>
            <Card v-for="order in store.orders" :key="order.id">
              <CardContent class="p-4 space-y-2">
                <div class="flex items-center justify-between">
                  <Badge :variant="statusVariant(order.status)">{{ statusLabel(order.status) }}</Badge>
                  <span class="text-xs text-muted-foreground">{{ new Date(order.received_at).toLocaleString('uz-UZ') }}</span>
                </div>
                <div class="space-y-1">
                  <div v-for="item in order.items" :key="item.name" class="flex justify-between text-sm">
                    <span>{{ item.name }} <span class="text-muted-foreground">×{{ item.qty }}</span></span>
                    <span class="tabular-nums font-mono text-xs">{{ money(item.price_minor_units * item.qty) }}</span>
                  </div>
                </div>
                <div class="flex justify-between text-sm font-semibold border-t pt-2">
                  <span>Jami</span>
                  <span class="tabular-nums">{{ money(order.total_minor_units) }}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </template>

    <!-- Password Dialog -->
    <Dialog :open="showPwModal" @update:open="v => { if (!auth.mustChangePassword) showPwModal = v }">
      <DialogContent class="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Parolni o'zgartirish</DialogTitle>
        </DialogHeader>
        <form @submit.prevent="changePassword" class="space-y-4">
          <p v-if="auth.mustChangePassword" class="text-xs text-muted-foreground">Xavfsizlik uchun parolingizni o'zgartiring.</p>
          <div class="space-y-2">
            <Label>Hozirgi parol (PIN)</Label>
            <Input v-model="pwCurrent" type="password" required />
          </div>
          <div class="space-y-2">
            <Label>Yangi parol</Label>
            <Input v-model="pwNew" type="password" required />
          </div>
          <div class="space-y-2">
            <Label>Yangi parolni tasdiqlang</Label>
            <Input v-model="pwConfirm" type="password" required />
          </div>
          <div v-if="pwError" class="rounded-md bg-destructive/10 text-destructive text-sm p-3">{{ pwError }}</div>
          <DialogFooter>
            <Button v-if="!auth.mustChangePassword" variant="outline" type="button" @click="showPwModal = false">Bekor</Button>
            <Button type="submit" :disabled="pwLoading">
              <Loader2 v-if="pwLoading" class="w-4 h-4 mr-2 animate-spin" />
              O'zgartirish
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  </div>
</template>
