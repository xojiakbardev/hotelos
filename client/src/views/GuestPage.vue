<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { receptionApi, type Guest, type GuestHistory, type Order, type Bill, type CleaningPreference } from '@/api/reception'
import { useToastStore } from '@/stores/toast'
import { useWsStore } from '@/stores/ws'
import { useAuthStore } from '@/stores/auth'
import { ROOM_TYPE_UZ } from '@/lib/labels'
import {
  Phone,
  BedDouble,
  Calendar,
  Clock,
  Sparkles,
  BellOff,
  Receipt,
  UtensilsCrossed,
  History,
  KeyRound,
  LogOut,
  Loader2,
  ArrowLeft,
  CheckCircle,
  Pencil,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()
const ws = useWsStore()
const auth = useAuthStore()

const guestId = computed(() => route.params.id as string)
const guest = ref<Guest | null>(null)
const orders = ref<Order[]>([])
const history = ref<GuestHistory | null>(null)
const loading = ref(true)
const resetting = ref(false)
const newPin = ref<string | null>(null)
const checkoutOpen = ref(false)
const checkingOut = ref(false)
const checkoutBill = ref<Bill | null>(null)

const editOpen = ref(false)
const editing = ref(false)
const editForm = ref({ full_name: '', phone: '', expected_checkout_at: '' })

function openEdit() {
  if (!guest.value) return
  editForm.value = {
    full_name: guest.value.full_name,
    phone: guest.value.phone,
    // <input type="datetime-local"> needs YYYY-MM-DDTHH:MM (no TZ).
    expected_checkout_at: new Date(guest.value.expected_checkout_at).toISOString().slice(0, 16),
  }
  editOpen.value = true
}

async function saveEdit() {
  if (!guest.value) return
  editing.value = true
  try {
    const updated = await receptionApi.updateGuest(guest.value.id, {
      full_name: editForm.value.full_name.trim(),
      phone: editForm.value.phone.trim(),
      expected_checkout_at: new Date(editForm.value.expected_checkout_at).toISOString(),
    })
    guest.value = { ...guest.value, ...updated }
    toast.success('Saqlandi')
    editOpen.value = false
  } catch (e: any) {
    toast.error(e?.response?.data?.detail?.message || e?.response?.data?.detail || 'Saqlashda xatolik')
  } finally {
    editing.value = false
  }
}

const canCheckOut = computed(() => auth.role === 'manager' || auth.role === 'reception')

const PREF_UZ: Record<string, string> = { morning: 'Ertalab', afternoon: 'Tushdan keyin', evening: 'Kechqurun', custom: 'Maxsus' }
const STATUS_UZ: Record<string, string> = { received: 'Qabul qilindi', preparing: 'Tayyorlanmoqda', delivering: 'Yetkazilmoqda', delivered: 'Yetkazildi' }

const savingPref = ref(false)

async function updateCleaningPreference(pref: string) {
  if (!guest.value) return
  savingPref.value = true
  try {
    const updated = await receptionApi.setCleaningPreference(guest.value.id, pref as CleaningPreference)
    guest.value.cleaning_preference = updated.cleaning_preference
    toast.success('Tozalash vaqti o\'zgartirildi')
  } catch {
    toast.error('O\'zgartirishda xatolik')
  } finally {
    savingPref.value = false
  }
}

function money(minor: number) { return (minor / 100).toLocaleString('uz-UZ') + " so'm" }
function nightsSoFar(g: Guest) { return Math.max(1, Math.ceil((Date.now() - new Date(g.checked_in_at).getTime()) / 86400000)) }
function nightsLeft(g: Guest) { return Math.max(0, Math.ceil((new Date(g.expected_checkout_at).getTime() - Date.now()) / 86400000)) }
function isEarly(g: Guest) { return nightsLeft(g) > 0 }

const roomTotal = computed(() => {
  if (!guest.value) return 0
  return nightsSoFar(guest.value) * guest.value.nightly_rate_locked_minor_units
})
const serviceTotal = computed(() => orders.value.reduce((s, o) => s + (o.status === 'delivered' ? o.total_minor_units : 0), 0))
const grandTotal = computed(() => roomTotal.value + serviceTotal.value)

async function loadData() {
  loading.value = true
  try {
    const g = await receptionApi.getGuest(guestId.value)
    guest.value = g
    // Load orders
    try {
      const allOrders = await receptionApi.listOrders()
      orders.value = allOrders.filter(o => o.guest_id === g.id)
    } catch { orders.value = [] }
    // Load history by phone
    try {
      history.value = await receptionApi.guestHistory(g.phone)
    } catch { history.value = null }
  } catch {
    toast.error("Mehmon ma'lumotlari yuklanmadi")
    router.back()
  } finally {
    loading.value = false
  }
}

async function resetPin() {
  if (!guest.value) return
  resetting.value = true
  try {
    const res = await receptionApi.resetGuestPin(guest.value.id)
    newPin.value = res.new_pin
    toast.info(`Yangi PIN: ${res.new_pin}`)
  } catch { toast.error('PIN tiklashda xatolik') }
  finally { resetting.value = false }
}

async function doCheckOut() {
  if (!guest.value) return
  checkingOut.value = true
  try {
    const bill = await receptionApi.checkOut(guest.value.id)
    checkoutBill.value = bill
    toast.success(`Mehmon chiqarildi`)
  } catch (e: any) {
    toast.error(e?.response?.data?.message || e?.response?.data?.detail || 'Check-out xatosi')
  } finally {
    checkingOut.value = false
  }
}

onMounted(loadData)

watch(() => ws.lastEvent, (env) => {
  const ch = env?.channel ?? ''
  if (ch.startsWith('orders.') || ch.startsWith('guests.')) loadData()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Back button -->
    <Button variant="ghost" size="sm" @click="router.push('/guests')">
      <ArrowLeft class="w-4 h-4 mr-1" />
      Mehmonlar
    </Button>

    <!-- Loading -->
    <div v-if="loading" class="space-y-4">
      <Skeleton class="h-8 w-64" />
      <div class="grid grid-cols-2 gap-4">
        <Skeleton class="h-32" />
        <Skeleton class="h-32" />
      </div>
    </div>

    <template v-else-if="guest">
      <!-- Header -->
      <div class="flex items-start justify-between">
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-2xl font-bold tracking-tight">{{ guest.full_name }}</h1>
            <Button
              v-if="canCheckOut && !guest.checked_out_at"
              variant="ghost"
              size="xs"
              @click="openEdit"
              title="Tahrirlash"
            >
              <Pencil class="w-3.5 h-3.5" />
            </Button>
          </div>
          <div class="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
            <span class="flex items-center gap-1"><Phone class="w-3.5 h-3.5" /> {{ guest.phone }}</span>
            <span class="flex items-center gap-1"><BedDouble class="w-3.5 h-3.5" /> #{{ guest.room_number }} · {{ guest.floor }}q</span>
          </div>
        </div>
        <Badge v-if="isEarly(guest)" variant="warning">{{ nightsLeft(guest) }} kun qoldi</Badge>
        <Badge v-else variant="destructive">Muddati tugagan</Badge>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Left column: info + billing -->
        <div class="lg:col-span-2 space-y-6">
          <!-- Stay info -->
          <Card>
            <CardHeader class="pb-3">
              <CardTitle class="text-sm font-semibold">Qolish ma'lumotlari</CardTitle>
            </CardHeader>
            <CardContent>
              <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <div class="flex items-center gap-2">
                  <BedDouble class="w-4 h-4 text-muted-foreground shrink-0" />
                  <div>
                    <p class="text-xs text-muted-foreground">Xona turi</p>
                    <p class="text-sm font-medium">{{ ROOM_TYPE_UZ[guest.room_type] || guest.room_type }}</p>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <Receipt class="w-4 h-4 text-muted-foreground shrink-0" />
                  <div>
                    <p class="text-xs text-muted-foreground">Tunlik narx</p>
                    <p class="text-sm font-medium text-primary">{{ money(guest.nightly_rate_locked_minor_units) }}</p>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <Clock class="w-4 h-4 text-muted-foreground shrink-0" />
                  <div>
                    <p class="text-xs text-muted-foreground">Yashagan</p>
                    <p class="text-sm font-medium">{{ nightsSoFar(guest) }} tun</p>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <Calendar class="w-4 h-4 text-muted-foreground shrink-0" />
                  <div>
                    <p class="text-xs text-muted-foreground">Kirgan</p>
                    <p class="text-sm font-medium">{{ new Date(guest.checked_in_at).toLocaleDateString('uz-UZ') }}</p>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <Calendar class="w-4 h-4 text-muted-foreground shrink-0" />
                  <div>
                    <p class="text-xs text-muted-foreground">Chiqishi kerak</p>
                    <p class="text-sm font-medium">{{ new Date(guest.expected_checkout_at).toLocaleDateString('uz-UZ') }}</p>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <Sparkles class="w-4 h-4 text-muted-foreground shrink-0" />
                  <div>
                    <p class="text-xs text-muted-foreground">Tozalash vaqti</p>
                    <Select
                      :model-value="guest.cleaning_preference"
                      :disabled="savingPref"
                      @update:model-value="updateCleaningPreference"
                    >
                      <SelectTrigger class="h-7 w-[140px] text-xs mt-0.5">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="morning">Ertalab</SelectItem>
                        <SelectItem value="afternoon">Tushdan keyin</SelectItem>
                        <SelectItem value="evening">Kechqurun</SelectItem>
                        <SelectItem value="custom">Maxsus</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
              <div v-if="guest.do_not_disturb" class="mt-3 flex items-center gap-2 text-amber-600">
                <BellOff class="w-4 h-4" />
                <span class="text-sm font-medium">Bezovta qilmaslik yoqilgan</span>
              </div>
            </CardContent>
          </Card>

          <!-- Billing -->
          <Card>
            <CardHeader class="pb-3">
              <CardTitle class="text-sm font-semibold flex items-center gap-2">
                <Receipt class="w-4 h-4 text-muted-foreground" />
                Joriy hisob
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div class="space-y-2">
                <div class="flex justify-between text-sm">
                  <span>Xona ({{ nightsSoFar(guest) }} × {{ money(guest.nightly_rate_locked_minor_units) }})</span>
                  <span class="font-mono tabular-nums">{{ money(roomTotal) }}</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="flex items-center gap-1"><UtensilsCrossed class="w-3.5 h-3.5" /> Xona xizmati ({{ orders.filter(o => o.status === 'delivered').length }})</span>
                  <span class="font-mono tabular-nums">{{ money(serviceTotal) }}</span>
                </div>
                <Separator />
                <div class="flex justify-between font-bold text-lg">
                  <span>Jami</span>
                  <span class="font-mono tabular-nums">{{ money(grandTotal) }}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <!-- Orders -->
          <Card>
            <CardHeader class="pb-3">
              <CardTitle class="text-sm font-semibold flex items-center gap-2">
                <UtensilsCrossed class="w-4 h-4 text-muted-foreground" />
                Buyurtmalar ({{ orders.length }})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div v-if="!orders.length" class="text-center py-6 text-muted-foreground text-sm">Buyurtmalar yo'q</div>
              <div v-else class="space-y-3">
                <div v-for="o in orders" :key="o.id" class="flex items-center justify-between py-2 border-b last:border-0">
                  <div class="flex items-center gap-3">
                    <Badge
                      :variant="o.status === 'delivered' ? 'success' : o.status === 'received' ? 'warning' : 'default'"
                      class="text-[10px]"
                    >
                      {{ STATUS_UZ[o.status] }}
                    </Badge>
                    <span class="text-sm">{{ o.items.map(i => `${i.qty}× ${i.name}`).join(', ') }}</span>
                  </div>
                  <span class="font-mono text-sm">{{ money(o.total_minor_units) }}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <!-- Right column: actions + history -->
        <div class="space-y-6">
          <!-- Actions -->
          <Card>
            <CardContent class="p-4 space-y-3">
              <Button
                v-if="canCheckOut"
                variant="destructive"
                class="w-full"
                @click="checkoutOpen = true"
              >
                <LogOut class="w-4 h-4 mr-2" />
                {{ isEarly(guest) ? 'Erta chiqarish' : 'Check-out' }}
              </Button>

              <div class="flex items-center justify-between bg-muted/40 rounded-lg p-3">
                <div>
                  <p class="text-xs text-muted-foreground">Self-service</p>
                  <p class="text-sm font-mono">{{ guest.phone }}</p>
                </div>
                <div class="flex items-center gap-2">
                  <span v-if="newPin" class="text-sm font-bold text-primary font-mono">{{ newPin }}</span>
                  <Button variant="outline" size="xs" :disabled="resetting" @click="resetPin">
                    <Loader2 v-if="resetting" class="w-3.5 h-3.5 animate-spin" />
                    <KeyRound v-else class="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <!-- History -->
          <Card v-if="history">
            <CardHeader class="pb-3">
              <CardTitle class="text-sm font-semibold flex items-center gap-2">
                <History class="w-4 h-4 text-muted-foreground" />
                Tashrif tarixi
              </CardTitle>
            </CardHeader>
            <CardContent class="space-y-3">
              <div class="flex flex-wrap gap-2">
                <Badge variant="secondary">{{ history.total_stays }} tashrif</Badge>
                <Badge variant="secondary">{{ history.total_nights }} tun</Badge>
                <Badge variant="secondary">{{ money(history.total_spent_minor_units) }}</Badge>
                <Badge v-if="history.repeat_visitor" variant="success">Doimiy</Badge>
              </div>
              <div class="space-y-2 max-h-48 overflow-y-auto">
                <div v-for="s in history.stays" :key="s.guest_id" class="flex items-center justify-between text-xs py-1.5 border-b last:border-0">
                  <span class="font-mono">#{{ s.room_number }}</span>
                  <span class="text-muted-foreground">{{ new Date(s.checked_in_at).toLocaleDateString('uz-UZ') }}</span>
                  <span>{{ s.nights }} tun</span>
                  <span class="font-mono">{{ s.total_minor_units ? money(s.total_minor_units) : '—' }}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </template>

    <!-- Check-out confirmation dialog -->
    <Dialog v-model:open="checkoutOpen">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Check-out tasdiqlash</DialogTitle>
          <DialogDescription class="sr-only">Mehmonni chiqarish uchun hisob-kitobni tasdiqlang</DialogDescription>
        </DialogHeader>

        <!-- Bill result -->
        <div v-if="checkoutBill" class="space-y-4">
          <div class="text-center space-y-2">
            <div class="w-12 h-12 rounded-full bg-green-100 dark:bg-green-900/30 grid place-items-center mx-auto">
              <CheckCircle class="w-6 h-6 text-green-600" />
            </div>
            <p class="font-semibold">Mehmon chiqarildi!</p>
          </div>
          <div class="bg-muted/40 rounded-lg p-4 space-y-2">
            <div class="flex justify-between text-sm"><span>Xona ({{ checkoutBill.nights }} tun)</span><span class="font-mono">{{ money(checkoutBill.room_cost_minor_units) }}</span></div>
            <div class="flex justify-between text-sm"><span>Xona xizmati</span><span class="font-mono">{{ money(checkoutBill.room_service_charges_minor_units) }}</span></div>
            <div v-if="checkoutBill.discount_minor_units" class="flex justify-between text-sm text-green-600"><span>Chegirma</span><span class="font-mono">-{{ money(checkoutBill.discount_minor_units) }}</span></div>
            <Separator />
            <div class="flex justify-between font-bold text-lg"><span>Jami</span><span class="font-mono">{{ money(checkoutBill.total_minor_units) }}</span></div>
          </div>
          <Button class="w-full" @click="checkoutOpen = false; router.push('/guests')">Yopish</Button>
        </div>

        <!-- Confirmation -->
        <div v-else class="space-y-4">
          <p class="text-sm text-muted-foreground">
            <strong>{{ guest?.full_name }}</strong> ni #{{ guest?.room_number }}-xonadan chiqarasizmi?
          </p>
          <div class="bg-muted/40 rounded-lg p-4 space-y-2">
            <div class="flex justify-between text-sm"><span>Xona ({{ guest ? nightsSoFar(guest) : 0 }} tun)</span><span class="font-mono">{{ money(roomTotal) }}</span></div>
            <div class="flex justify-between text-sm"><span>Xona xizmati</span><span class="font-mono">{{ money(serviceTotal) }}</span></div>
            <Separator />
            <div class="flex justify-between font-bold"><span>Taxminiy jami</span><span class="font-mono">{{ money(grandTotal) }}</span></div>
          </div>
          <p v-if="guest && isEarly(guest)" class="text-xs text-amber-600">
            ⚠️ Muddatidan {{ nightsLeft(guest) }} kun oldin chiqarilmoqda
          </p>
          <div class="flex gap-3">
            <Button variant="outline" class="flex-1" @click="checkoutOpen = false">Bekor</Button>
            <Button variant="destructive" class="flex-1" :disabled="checkingOut" @click="doCheckOut">
              <Loader2 v-if="checkingOut" class="w-4 h-4 mr-2 animate-spin" />
              Tasdiqlash
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>

    <!-- Edit guest dialog -->
    <Dialog v-model:open="editOpen">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Mehmonni tahrirlash</DialogTitle>
          <DialogDescription class="sr-only">Mehmon ma'lumotlarini yangilang</DialogDescription>
        </DialogHeader>
        <form class="space-y-4" @submit.prevent="saveEdit">
          <div class="space-y-1.5">
            <Label for="edit-name">F.I.Sh.</Label>
            <Input id="edit-name" v-model="editForm.full_name" required minlength="2" maxlength="120" />
          </div>
          <div class="space-y-1.5">
            <Label for="edit-phone">Telefon</Label>
            <Input id="edit-phone" v-model="editForm.phone" required placeholder="+998901234567" />
          </div>
          <div class="space-y-1.5">
            <Label for="edit-checkout">Chiqishi kerak</Label>
            <Input id="edit-checkout" v-model="editForm.expected_checkout_at" type="datetime-local" required />
          </div>
          <div class="flex gap-3 pt-2">
            <Button type="button" variant="outline" class="flex-1" @click="editOpen = false">Bekor</Button>
            <Button type="submit" class="flex-1" :disabled="editing">
              <Loader2 v-if="editing" class="w-4 h-4 mr-2 animate-spin" />
              Saqlash
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  </div>
</template>
