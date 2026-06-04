<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Separator } from '@/components/ui/separator'
import { receptionApi, type Guest, type GuestHistory, type Order } from '@/api/reception'
import { useToastStore } from '@/stores/toast'
import { ROOM_TYPE_UZ } from '@/lib/labels'
import { KeyRound, Loader2 } from 'lucide-vue-next'

const props = defineProps<{ guest: Guest | null; open: boolean }>()
const emit = defineEmits<{ close: [] }>()

const toast = useToastStore()
const history = ref<GuestHistory | null>(null)
const orders = ref<Order[]>([])
const loadingHistory = ref(false)
const newPin = ref<string | null>(null)
const resetting = ref(false)

// Keep last guest data visible during close animation
const displayGuest = ref<Guest | null>(null)
watch(() => props.guest, (g) => {
  if (g) {
    displayGuest.value = g
    loadData()
    newPin.value = null
  }
}, { immediate: true })

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

async function loadData() {
  if (!props.guest) return
  loadingHistory.value = true
  try {
    const [h, allOrders] = await Promise.all([
      receptionApi.guestHistory(props.guest.phone).catch(() => null),
      receptionApi.listOrders().catch(() => [] as Order[])
    ])
    history.value = h
    orders.value = allOrders.filter(o => o.guest_id === props.guest!.id)
  } finally { loadingHistory.value = false }
}

const PREF_UZ: Record<string, string> = { morning: 'Ertalab', afternoon: 'Tushdan keyin', evening: 'Kechqurun', custom: 'Maxsus' }
const STATUS_UZ: Record<string, string> = { received: 'Qabul qilindi', preparing: 'Tayyorlanmoqda', delivering: 'Yetkazilmoqda', delivered: 'Yetkazildi' }

function money(minor: number) { return (minor / 100).toLocaleString('uz-UZ') + " so'm" }
function nightsSoFar(g: Guest) { return Math.max(1, Math.ceil((Date.now() - new Date(g.checked_in_at).getTime()) / 86400000)) }
function nightsLeft(g: Guest) { return Math.max(0, Math.ceil((new Date(g.expected_checkout_at).getTime() - Date.now()) / 86400000)) }
</script>

<template>
  <Dialog :open="open" @update:open="(v: boolean) => { if (!v) emit('close') }">
    <DialogContent class="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle>{{ displayGuest?.full_name || 'Mehmon' }}</DialogTitle>
      </DialogHeader>

      <Tabs v-if="displayGuest" default-value="info" class="mt-2">
        <TabsList>
          <TabsTrigger value="info">Ma'lumotlar</TabsTrigger>
          <TabsTrigger value="orders">Buyurtmalar ({{ orders.length }})</TabsTrigger>
          <TabsTrigger value="history">Tarix</TabsTrigger>
        </TabsList>

        <!-- Info Tab -->
        <TabsContent value="info" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div><p class="text-xs uppercase text-muted-foreground font-semibold">Telefon</p><p class="font-mono text-sm">{{ displayGuest.phone }}</p></div>
            <div><p class="text-xs uppercase text-muted-foreground font-semibold">Xona</p><p class="text-sm">#{{ displayGuest.room_number }} · {{ displayGuest.floor }}q</p></div>
            <div><p class="text-xs uppercase text-muted-foreground font-semibold">Xona turi</p><p class="text-sm">{{ ROOM_TYPE_UZ[guest.room_type] || guest.room_type }}</p></div>
            <div><p class="text-xs uppercase text-muted-foreground font-semibold">Tunlik narx</p><p class="text-sm font-semibold text-primary">{{ money(guest.nightly_rate_locked_minor_units) }}</p></div>
            <div><p class="text-xs uppercase text-muted-foreground font-semibold">Qabul qilingan</p><p class="text-sm">{{ new Date(guest.checked_in_at).toLocaleString('uz-UZ') }}</p></div>
            <div><p class="text-xs uppercase text-muted-foreground font-semibold">Chiqish</p><p class="text-sm">{{ new Date(guest.expected_checkout_at).toLocaleString('uz-UZ') }}</p></div>
            <div><p class="text-xs uppercase text-muted-foreground font-semibold">Yashagan</p><p class="text-sm">{{ nightsSoFar(displayGuest!) }} tun</p></div>
            <div><p class="text-xs uppercase text-muted-foreground font-semibold">Qolgan</p><p class="text-sm">{{ nightsLeft(displayGuest!) }} kun</p></div>
            <div><p class="text-xs uppercase text-muted-foreground font-semibold">Tozalash</p><p class="text-sm">{{ PREF_UZ[guest.cleaning_preference] || guest.cleaning_preference }}</p></div>
            <div><p class="text-xs uppercase text-muted-foreground font-semibold">DND</p><p :class="displayGuest.do_not_disturb ? 'text-sm text-amber-600 font-medium' : 'text-sm'">{{ displayGuest.do_not_disturb ? 'Yoqilgan' : "O'chiq" }}</p></div>
          </div>

          <Separator />

          <!-- Cost summary -->
          <div class="bg-muted/50 rounded-lg p-4 space-y-2">
            <p class="text-xs font-semibold text-muted-foreground uppercase">Joriy hisob</p>
            <div class="flex justify-between text-sm"><span>Xona ({{ nightsSoFar(displayGuest!) }} × {{ money(guest.nightly_rate_locked_minor_units) }})</span><span class="tabular-nums font-mono">{{ money(nightsSoFar(displayGuest!) * guest.nightly_rate_locked_minor_units) }}</span></div>
            <div class="flex justify-between text-sm"><span>Xona xizmati</span><span class="tabular-nums font-mono">{{ money(orders.reduce((s, o) => s + (o.status === 'delivered' ? o.total_minor_units : 0), 0)) }}</span></div>
            <div class="flex justify-between text-sm font-bold border-t pt-2"><span>Jami</span><span class="tabular-nums font-mono">{{ money(nightsSoFar(displayGuest!) * guest.nightly_rate_locked_minor_units + orders.reduce((s, o) => s + (o.status === 'delivered' ? o.total_minor_units : 0), 0)) }}</span></div>
          </div>

          <!-- PIN -->
          <div class="bg-muted/50 rounded-lg p-4 space-y-2">
            <p class="text-xs font-semibold text-muted-foreground uppercase">Self-service kirish</p>
            <div class="flex justify-between items-center text-sm"><span>Login</span><span class="font-mono">{{ displayGuest.phone }}</span></div>
            <div v-if="newPin" class="flex justify-between items-center"><span class="text-sm">Yangi PIN</span><span class="text-lg font-bold text-primary font-mono tracking-widest">{{ newPin }}</span></div>
            <Button variant="outline" size="sm" :disabled="resetting" @click="resetPin">
              <Loader2 v-if="resetting" class="w-4 h-4 mr-2 animate-spin" />
              <KeyRound v-else class="w-4 h-4 mr-2" />
              PIN tiklash
            </Button>
          </div>
        </TabsContent>

        <!-- Orders Tab -->
        <TabsContent value="orders">
          <div v-if="!orders.length" class="text-center py-8 text-muted-foreground text-sm">Buyurtmalar yo'q</div>
          <div v-else class="space-y-3">
            <div v-for="o in orders" :key="o.id" class="border rounded-lg p-3 space-y-2">
              <div class="flex justify-between items-center">
                <Badge :variant="o.status === 'delivered' ? 'success' : 'default'">{{ STATUS_UZ[o.status] || o.status }}</Badge>
                <span class="font-mono text-sm font-semibold">{{ money(o.total_minor_units) }}</span>
              </div>
              <div class="flex flex-wrap gap-1">
                <Badge v-for="item in o.items" :key="item.name" variant="secondary" class="text-xs">{{ item.name }} ×{{ item.qty }}</Badge>
              </div>
              <p class="text-xs text-muted-foreground">{{ new Date(o.received_at).toLocaleString('uz-UZ') }}</p>
            </div>
          </div>
        </TabsContent>

        <!-- History Tab -->
        <TabsContent value="history">
          <div v-if="loadingHistory" class="text-center py-8 text-muted-foreground">Yuklanmoqda...</div>
          <div v-else-if="!history || !history.stays.length" class="text-center py-8 text-muted-foreground text-sm">Tarix topilmadi</div>
          <template v-else>
            <div class="flex flex-wrap gap-2 mb-4">
              <Badge variant="secondary">{{ history.total_stays }} tashrif</Badge>
              <Badge variant="secondary">{{ history.total_nights }} tun</Badge>
              <Badge variant="secondary">{{ money(history.total_spent_minor_units) }}</Badge>
              <Badge v-if="history.repeat_visitor" variant="success">Doimiy mehmon</Badge>
            </div>
            <div class="space-y-2">
              <div v-for="s in history.stays" :key="s.guest_id" class="flex items-center justify-between text-sm py-2 border-b last:border-0">
                <span class="font-mono">#{{ s.room_number }}</span>
                <span>{{ new Date(s.checked_in_at).toLocaleDateString('uz-UZ') }}</span>
                <span>{{ s.nights }} tun</span>
                <span class="font-mono">{{ s.total_minor_units ? money(s.total_minor_units) : '—' }}</span>
              </div>
            </div>
          </template>
        </TabsContent>
      </Tabs>
    </DialogContent>
  </Dialog>
</template>
