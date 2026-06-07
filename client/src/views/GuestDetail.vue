<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { receptionApi, type Guest, type GuestHistory, type Order, type Bill } from '@/api/reception'
import { useToastStore } from '@/stores/toast'
import { useAuthStore } from '@/stores/auth'
import { ROOM_TYPE_UZ } from '@/lib/labels'
import {
  KeyRound,
  Loader2,
  LogOut,
  Phone,
  BedDouble,
  Calendar,
  Clock,
  Sparkles,
  BellOff,
  Receipt,
  UtensilsCrossed,
  History,
} from 'lucide-vue-next'

const props = defineProps<{ guest: Guest | null; open: boolean }>()
const emit = defineEmits<{ close: []; checked_out: [] }>()

const toast = useToastStore()
const auth = useAuthStore()
const router = useRouter()

const orders = ref<Order[]>([])
const history = ref<GuestHistory | null>(null)
const loadingHistory = ref(false)
const newPin = ref<string | null>(null)
const resetting = ref(false)
const checkingOut = ref(false)
const checkoutBill = ref<Bill | null>(null)

const canCheckOut = computed(() => auth.role === 'manager' || auth.role === 'reception')

// Keep last guest data visible during close animation
const displayGuest = ref<Guest | null>(null)
watch(() => props.guest, (g) => {
  if (g) {
    displayGuest.value = g
    checkoutBill.value = null
    newPin.value = null
    loadData()
  }
}, { immediate: true })

async function loadData() {
  if (!props.guest) return
  loadingHistory.value = true
  try {
    const [h, guestOrders] = await Promise.all([
      receptionApi.guestHistory(props.guest.phone).catch(() => null),
      receptionApi.listOrdersByGuest(props.guest.id).catch(() => [] as Order[])
    ])
    history.value = h
    orders.value = guestOrders
  } finally { loadingHistory.value = false }
}

async function resetPin() {
  if (!props.guest) return
  resetting.value = true
  try {
    const res = await receptionApi.resetGuestPin(props.guest.id)
    newPin.value = res.new_pin
    toast.info(`Yangi PIN: ${res.new_pin}`)
  } catch { toast.error('PIN tiklashda xatolik') }
  finally { resetting.value = false }
}

async function checkOut() {
  if (!props.guest) return
  checkingOut.value = true
  try {
    const bill = await receptionApi.checkOut(props.guest.id)
    checkoutBill.value = bill
    toast.success(`Mehmon chiqarildi. Hisob: ${money(bill.total_minor_units)}`)
    emit('checked_out')
  } catch (e: any) {
    const msg = e?.response?.data?.message || e?.response?.data?.detail || 'Check-out xatosi'
    toast.error(msg)
  } finally {
    checkingOut.value = false
  }
}

const PREF_UZ: Record<string, string> = { morning: 'Ertalab', afternoon: 'Tushdan keyin', evening: 'Kechqurun', custom: 'Maxsus' }
const STATUS_UZ: Record<string, string> = { received: 'Qabul qilindi', preparing: 'Tayyorlanmoqda', delivering: 'Yetkazilmoqda', delivered: 'Yetkazildi' }

function money(minor: number) { return (minor / 100).toLocaleString('uz-UZ') + " so'm" }

function nightsSoFar(g: Guest) {
  return Math.max(1, Math.ceil((Date.now() - new Date(g.checked_in_at).getTime()) / 86400000))
}

function nightsLeft(g: Guest) {
  return Math.max(0, Math.ceil((new Date(g.expected_checkout_at).getTime() - Date.now()) / 86400000))
}

function isEarlyCheckout(g: Guest) {
  return nightsLeft(g) > 0
}

const roomTotal = computed(() => {
  if (!displayGuest.value) return 0
  return nightsSoFar(displayGuest.value) * displayGuest.value.nightly_rate_locked_minor_units
})

const serviceTotal = computed(() =>
  orders.value.reduce((s, o) => s + o.total_minor_units, 0),
)

const grandTotal = computed(() => roomTotal.value + serviceTotal.value)
</script>

<template>
  <Dialog :open="open" @update:open="(v: boolean) => { if (!v) emit('close') }">
    <DialogContent class="sm:max-w-xl max-h-[90vh] overflow-y-auto p-0">
      <!-- Header -->
      <div class="px-6 pt-6 pb-4 border-b">
        <div class="flex items-start justify-between">
          <div>
            <DialogTitle class="text-xl font-bold">{{ displayGuest?.full_name || 'Mehmon' }}</DialogTitle>
            <div class="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
              <span class="flex items-center gap-1"><Phone class="w-3.5 h-3.5" /> {{ displayGuest?.phone }}</span>
              <span class="flex items-center gap-1"><BedDouble class="w-3.5 h-3.5" /> #{{ displayGuest?.room_number }}</span>
            </div>
          </div>
          <Badge v-if="displayGuest && isEarlyCheckout(displayGuest)" variant="warning" class="shrink-0">
            {{ nightsLeft(displayGuest) }} kun qoldi
          </Badge>
          <Badge v-else-if="displayGuest" variant="destructive" class="shrink-0">
            Muddati tugagan
          </Badge>
        </div>
      </div>

      <!-- Checkout bill shown after success -->
      <div v-if="checkoutBill" class="px-6 py-6 space-y-4">
        <div class="text-center space-y-2">
          <div class="w-12 h-12 rounded-full bg-green-100 dark:bg-green-900/30 grid place-items-center mx-auto">
            <Receipt class="w-6 h-6 text-green-600" />
          </div>
          <h3 class="text-lg font-bold">Mehmon chiqarildi</h3>
        </div>
        <Card>
          <CardContent class="p-4 space-y-2">
            <div class="flex justify-between text-sm"><span>Xona ({{ checkoutBill.nights }} tun)</span><span class="font-mono tabular-nums">{{ money(checkoutBill.room_cost_minor_units) }}</span></div>
            <div class="flex justify-between text-sm"><span>Xona xizmati</span><span class="font-mono tabular-nums">{{ money(checkoutBill.room_service_charges_minor_units) }}</span></div>
            <div v-if="checkoutBill.extras_minor_units" class="flex justify-between text-sm"><span>Qo'shimcha</span><span class="font-mono tabular-nums">{{ money(checkoutBill.extras_minor_units) }}</span></div>
            <div v-if="checkoutBill.discount_minor_units" class="flex justify-between text-sm text-green-600"><span>Chegirma</span><span class="font-mono tabular-nums">-{{ money(checkoutBill.discount_minor_units) }}</span></div>
            <Separator />
            <div class="flex justify-between font-bold"><span>Jami</span><span class="font-mono tabular-nums text-lg">{{ money(checkoutBill.total_minor_units) }}</span></div>
          </CardContent>
        </Card>
        <Button class="w-full" @click="emit('close')">Yopish</Button>
      </div>

      <!-- Main content (before checkout) -->
      <div v-else class="px-6 py-4 space-y-5">
        <!-- Stay info grid -->
        <div class="grid grid-cols-2 gap-x-6 gap-y-3">
          <div class="flex items-center gap-2">
            <BedDouble class="w-4 h-4 text-muted-foreground shrink-0" />
            <div>
              <p class="text-xs text-muted-foreground">Xona turi</p>
              <p class="text-sm font-medium">{{ ROOM_TYPE_UZ[displayGuest?.room_type || ''] || displayGuest?.room_type }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <Receipt class="w-4 h-4 text-muted-foreground shrink-0" />
            <div>
              <p class="text-xs text-muted-foreground">Tunlik narx</p>
              <p class="text-sm font-medium text-primary">{{ displayGuest ? money(displayGuest.nightly_rate_locked_minor_units) : '—' }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <Calendar class="w-4 h-4 text-muted-foreground shrink-0" />
            <div>
              <p class="text-xs text-muted-foreground">Kirgan</p>
              <p class="text-sm font-medium">{{ displayGuest ? new Date(displayGuest.checked_in_at).toLocaleDateString('uz-UZ') : '—' }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <Calendar class="w-4 h-4 text-muted-foreground shrink-0" />
            <div>
              <p class="text-xs text-muted-foreground">Chiqishi kerak</p>
              <p class="text-sm font-medium">{{ displayGuest ? new Date(displayGuest.expected_checkout_at).toLocaleDateString('uz-UZ') : '—' }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <Clock class="w-4 h-4 text-muted-foreground shrink-0" />
            <div>
              <p class="text-xs text-muted-foreground">Yashagan</p>
              <p class="text-sm font-medium">{{ displayGuest ? nightsSoFar(displayGuest) : 0 }} tun</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <Sparkles class="w-4 h-4 text-muted-foreground shrink-0" />
            <div>
              <p class="text-xs text-muted-foreground">Tozalash</p>
              <p class="text-sm font-medium">{{ PREF_UZ[displayGuest?.cleaning_preference || ''] || '—' }}</p>
            </div>
          </div>
          <div v-if="displayGuest?.do_not_disturb" class="col-span-2 flex items-center gap-2">
            <BellOff class="w-4 h-4 text-amber-600 shrink-0" />
            <p class="text-sm font-medium text-amber-600">Bezovta qilmaslik yoqilgan</p>
          </div>
        </div>

        <Separator />

        <!-- Hisob -->
        <div class="space-y-2">
          <div class="flex items-center gap-2 mb-2">
            <Receipt class="w-4 h-4 text-muted-foreground" />
            <h3 class="text-sm font-semibold">Joriy hisob</h3>
          </div>
          <div class="bg-muted/40 rounded-lg p-4 space-y-2">
            <div class="flex justify-between text-sm">
              <span>Xona ({{ displayGuest ? nightsSoFar(displayGuest) : 0 }} × {{ displayGuest ? money(displayGuest.nightly_rate_locked_minor_units) : '—' }})</span>
              <span class="font-mono tabular-nums">{{ money(roomTotal) }}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="flex items-center gap-1"><UtensilsCrossed class="w-3.5 h-3.5" /> Xona xizmati ({{ orders.length }})</span>
              <span class="font-mono tabular-nums">{{ money(serviceTotal) }}</span>
            </div>
            <Separator />
            <div class="flex justify-between font-bold text-base">
              <span>Jami</span>
              <span class="font-mono tabular-nums">{{ money(grandTotal) }}</span>
            </div>
          </div>
        </div>

        <!-- Orders quick view -->
        <div v-if="orders.length" class="space-y-2">
          <div class="flex items-center gap-2">
            <UtensilsCrossed class="w-4 h-4 text-muted-foreground" />
            <h3 class="text-sm font-semibold">Buyurtmalar ({{ orders.length }})</h3>
          </div>
          <div class="space-y-2 max-h-32 overflow-y-auto">
            <div v-for="o in orders" :key="o.id" class="flex items-center justify-between py-1.5 px-2 rounded border text-sm">
              <div class="flex items-center gap-2">
                <Badge :variant="o.status === 'delivered' ? 'success' : o.status === 'received' ? 'warning' : 'default'" class="text-[10px]">
                  {{ STATUS_UZ[o.status] }}
                </Badge>
                <span class="text-xs text-muted-foreground">{{ o.items.map(i => i.name).join(', ') }}</span>
              </div>
              <span class="font-mono text-xs">{{ money(o.total_minor_units) }}</span>
            </div>
          </div>
        </div>

        <!-- History badge -->
        <div v-if="history && history.repeat_visitor" class="flex items-center gap-2">
          <History class="w-4 h-4 text-muted-foreground" />
          <Badge variant="success">Doimiy mehmon · {{ history.total_stays }} tashrif</Badge>
        </div>

        <!-- Self-service -->
        <div class="space-y-2">
          <div class="flex items-center gap-2">
            <KeyRound class="w-4 h-4 text-muted-foreground" />
            <h3 class="text-sm font-semibold">Self-service</h3>
          </div>
          <div class="flex items-center justify-between bg-muted/40 rounded-lg p-3">
            <span class="text-sm font-mono">{{ displayGuest?.phone }}</span>
            <div class="flex items-center gap-2">
              <span v-if="newPin" class="text-sm font-bold text-primary font-mono tracking-widest">{{ newPin }}</span>
              <Button variant="outline" size="xs" :disabled="resetting" @click="resetPin">
                <Loader2 v-if="resetting" class="w-3.5 h-3.5 mr-1 animate-spin" />
                <KeyRound v-else class="w-3.5 h-3.5 mr-1" />
                PIN tiklash
              </Button>
            </div>
          </div>
        </div>

        <Separator />

        <!-- Actions -->
        <div class="flex gap-3">
          <Button
            v-if="canCheckOut"
            variant="destructive"
            class="flex-1"
            :disabled="checkingOut"
            @click="checkOut"
          >
            <Loader2 v-if="checkingOut" class="w-4 h-4 mr-2 animate-spin" />
            <LogOut v-else class="w-4 h-4 mr-2" />
            {{ isEarlyCheckout(displayGuest!) ? 'Erta chiqarish' : 'Check-out' }}
          </Button>
          <Button variant="outline" class="flex-1" @click="emit('close')">
            Yopish
          </Button>
        </div>

        <p v-if="canCheckOut && displayGuest && isEarlyCheckout(displayGuest)" class="text-xs text-muted-foreground text-center">
          Muddatidan {{ nightsLeft(displayGuest) }} kun oldin. Hisob faqat yashagan kunlar uchun hisoblanadi.
        </p>
      </div>
    </DialogContent>
  </Dialog>
</template>
