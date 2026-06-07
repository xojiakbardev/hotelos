<script setup lang="ts">
import { useRouter } from 'vue-router'
import { computed, onMounted, ref, watch } from 'vue'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator } from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Skeleton } from '@/components/ui/skeleton'
import CheckInForm from './CheckInForm.vue'
import { receptionApi, type Guest, type Order, type Bill } from '@/api/reception'
import { useGuestsStore } from '@/stores/guests'
import { useWsStore } from '@/stores/ws'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { UserPlus, Search, MoreVertical, Eye, LogOut, Trash2, Loader2, CheckCircle } from 'lucide-vue-next'

const guests = useGuestsStore()
const ws = useWsStore()
const auth = useAuthStore()
const toast = useToastStore()
const router = useRouter()

const checkInOpen = ref(false)
const searchQuery = ref('')
const filterFloor = ref('all')
const filterStatus = ref('active') // 'active' | 'checked_out' | 'all'
const filterDate = ref('') // yyyy-mm-dd format or empty

onMounted(() => guests.load(filterStatus.value === 'active' ? undefined : filterStatus.value as any))

watch(filterStatus, (val) => {
  guests.load(val === 'active' ? undefined : val as any)
})

watch(
  () => ws.lastEvent,
  (env) => {
    const ch = env?.channel ?? ''
    if (ch.startsWith('guests.') || ch.startsWith('bills.')) guests.load(filterStatus.value === 'active' ? undefined : filterStatus.value as any)
  }
)

// Checkout modal
const checkoutGuest = ref<Guest | null>(null)
const checkoutOpen = ref(false)
const checkoutOrders = ref<Order[]>([])
const checkingOut = ref(false)
const checkoutBill = ref<Bill | null>(null)

// Delete modal
const deleteGuest = ref<Guest | null>(null)
const deleteOpen = ref(false)
const deleting = ref(false)

const filteredGuests = computed(() => {
  let list = guests.guests
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(g =>
      g.full_name.toLowerCase().includes(q) ||
      g.phone.includes(q) ||
      String(g.room_number).includes(q)
    )
  }
  if (filterFloor.value !== 'all') {
    list = list.filter(g => String(g.floor) === filterFloor.value)
  }
  if (filterDate.value) {
    list = list.filter(g => {
      const checkedIn = g.checked_in_at.slice(0, 10)
      const checkedOut = g.checked_out_at ? g.checked_out_at.slice(0, 10) : null
      return checkedIn === filterDate.value || checkedOut === filterDate.value
    })
  }
  return list
})

const floors = computed(() => {
  const set = new Set(guests.guests.map(g => g.floor))
  return [...set].sort((a, b) => a - b)
})

const totalRevenuePotential = computed(() =>
  guests.guests.reduce((s, g) => s + g.nightly_rate_locked_minor_units, 0)
)

function onCheckInSuccess() {
  checkInOpen.value = false
  guests.load()
}

function closeCheckIn() {
  checkInOpen.value = false
}

function money(minor: number) { return (minor / 100).toLocaleString('uz-UZ') + " so'm" }

function nightsSoFar(g: Guest) {
  const ms = Date.now() - new Date(g.checked_in_at).getTime()
  return Math.max(1, Math.ceil(ms / (24 * 3600 * 1000)))
}

function nightsLeft(g: Guest) {
  return Math.max(0, Math.ceil((new Date(g.expected_checkout_at).getTime() - Date.now()) / 86400000))
}

async function openCheckout(g: Guest) {
  checkoutGuest.value = g
  checkoutBill.value = null
  checkingOut.value = false
  checkoutOpen.value = true
  try {
    const allOrders = await receptionApi.listOrders()
    checkoutOrders.value = allOrders.filter(o => o.guest_id === g.id)
  } catch { checkoutOrders.value = [] }
}

const checkoutRoomTotal = computed(() => {
  if (!checkoutGuest.value) return 0
  return nightsSoFar(checkoutGuest.value) * checkoutGuest.value.nightly_rate_locked_minor_units
})
const checkoutServiceTotal = computed(() => checkoutOrders.value.reduce((s, o) => s + (o.status === 'delivered' ? o.total_minor_units : 0), 0))
const checkoutGrandTotal = computed(() => checkoutRoomTotal.value + checkoutServiceTotal.value)

async function doCheckOut() {
  if (!checkoutGuest.value) return
  checkingOut.value = true
  try {
    const bill = await receptionApi.checkOut(checkoutGuest.value.id)
    checkoutBill.value = bill
    toast.success('Mehmon chiqarildi')
    guests.load()
  } catch (e: any) {
    toast.error(e?.response?.data?.message || e?.response?.data?.detail || 'Check-out xatosi')
  } finally {
    checkingOut.value = false
  }
}

async function doDelete() {
  if (!deleteGuest.value) return
  deleting.value = true
  try {
    await receptionApi.checkOut(deleteGuest.value.id)
    toast.info("Mehmon o'chirildi")
    deleteOpen.value = false
    guests.load()
  } catch (e: any) {
    toast.error(e?.response?.data?.message || "O'chirishda xatolik")
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Stats -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <Card>
        <CardContent class="p-5">
          <p class="text-sm text-muted-foreground">Faol mehmonlar</p>
          <p class="text-2xl font-bold mt-1">{{ guests.guests.length }}</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent class="p-5">
          <p class="text-sm text-muted-foreground">Tunlik potentsial</p>
          <p class="text-2xl font-bold mt-1">{{ money(totalRevenuePotential) }}</p>
        </CardContent>
      </Card>
    </div>

    <!-- Filters + actions -->
    <Card>
      <CardContent class="p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div class="flex gap-3 items-center">
          <div class="relative">
            <Search class="absolute left-2.5 top-2.5 w-4 h-4 text-muted-foreground" />
            <Input
              v-model="searchQuery"
              placeholder="Ism, telefon yoki xona..."
              class="pl-9 w-[240px]"
            />
          </div>
          <Select v-model="filterStatus">
            <SelectTrigger class="w-[160px]">
              <SelectValue placeholder="Holat" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="active">Faol mehmonlar</SelectItem>
              <SelectItem value="checked_out">Ketganlar</SelectItem>
              <SelectItem value="all">Hammasi</SelectItem>
            </SelectContent>
          </Select>
          <Select v-model="filterFloor">
            <SelectTrigger class="w-[140px]">
              <SelectValue placeholder="Qavat" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Barcha qavatlar</SelectItem>
              <SelectItem v-for="f in floors" :key="f" :value="String(f)">{{ f }}-qavat</SelectItem>
            </SelectContent>
          </Select>
          <Input
            v-model="filterDate"
            type="date"
            class="w-[160px]"
            placeholder="Sana"
          />
        </div>
        <Button size="sm" @click="checkInOpen = true">
          <UserPlus class="w-4 h-4 mr-1" />
          Yangi mehmon
        </Button>
      </CardContent>
    </Card>

    <!-- States -->
    <div v-if="guests.error" class="rounded-md bg-destructive/10 text-destructive text-sm p-4">
      {{ guests.error }}
    </div>
    <div v-if="guests.loading && !guests.guests.length" class="space-y-3">
      <Card>
        <div class="p-4 space-y-4">
          <div v-for="i in 5" :key="i" class="flex items-center gap-4">
            <Skeleton class="h-7 w-7 rounded-full" />
            <Skeleton class="h-4 w-32" />
            <Skeleton class="h-4 w-28 ml-auto" />
            <Skeleton class="h-4 w-16" />
            <Skeleton class="h-4 w-12" />
            <Skeleton class="h-4 w-20" />
          </div>
        </div>
      </Card>
    </div>
    <div v-else-if="!filteredGuests.length" class="text-center py-12 text-muted-foreground">
      {{ searchQuery || filterFloor !== 'all' ? 'Filtrga mos mehmon topilmadi.' : "Hozircha faol mehmonlar yo'q." }}
    </div>

    <!-- Table -->
    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Mehmon</TableHead>
            <TableHead>Holat</TableHead>
            <TableHead>Telefon</TableHead>
            <TableHead>Xona</TableHead>
            <TableHead>Qabul qilindi</TableHead>
            <TableHead class="text-right">Tunlar</TableHead>
            <TableHead class="text-right">Narx/tun</TableHead>
            <TableHead>Chiqish sanasi</TableHead>
            <TableHead class="w-10"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow
            v-for="g in filteredGuests"
            :key="g.id"
            class="cursor-pointer"
            @click="router.push(`/guests/${g.id}`)"
          >
            <TableCell>
              <div class="flex items-center gap-2.5">
                <Avatar class="h-7 w-7">
                  <AvatarFallback class="text-xs bg-primary/10 text-primary">
                    {{ g.full_name.slice(0, 1).toUpperCase() }}
                  </AvatarFallback>
                </Avatar>
                <span class="font-medium">{{ g.full_name }}</span>
              </div>
            </TableCell>
            <TableCell>
              <Badge v-if="!g.checked_out_at" variant="success" class="text-[10px]">Faol</Badge>
              <Badge v-else variant="secondary" class="text-[10px]">Ketgan</Badge>
            </TableCell>
            <TableCell class="text-muted-foreground font-mono text-xs">{{ g.phone }}</TableCell>
            <TableCell class="font-mono">
              #{{ g.room_number }}
              <span class="text-muted-foreground"> / {{ g.floor }}q</span>
            </TableCell>
            <TableCell class="text-muted-foreground">{{ new Date(g.checked_in_at).toLocaleDateString('uz-UZ') }}</TableCell>
            <TableCell class="text-right font-mono tabular-nums">{{ nightsSoFar(g) }}</TableCell>
            <TableCell class="text-right font-mono tabular-nums">{{ money(g.nightly_rate_locked_minor_units) }}</TableCell>
            <TableCell class="text-muted-foreground">{{ new Date(g.expected_checkout_at).toLocaleDateString('uz-UZ') }}</TableCell>
            <TableCell @click.stop>
              <DropdownMenu>
                <DropdownMenuTrigger as-child>
                  <Button variant="ghost" size="icon-sm">
                    <MoreVertical class="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem @click="router.push(`/guests/${g.id}`)">
                    <Eye class="w-4 h-4 mr-2" />
                    Batafsil
                  </DropdownMenuItem>
                  <DropdownMenuItem @click="openCheckout(g)">
                    <LogOut class="w-4 h-4 mr-2" />
                    Check-out
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem class="text-destructive focus:text-destructive" @click="deleteGuest = g; deleteOpen = true">
                    <Trash2 class="w-4 h-4 mr-2" />
                    O'chirish
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>

    <!-- Check-in Dialog -->
    <Dialog v-model:open="checkInOpen">
      <DialogContent class="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Mehmonni qabul qilish</DialogTitle>
          <DialogDescription class="sr-only">Yangi mehmonni ro'yxatdan o'tkazish formasi</DialogDescription>
        </DialogHeader>
        <CheckInForm @cancel="closeCheckIn" @success="onCheckInSuccess" />
      </DialogContent>
    </Dialog>

    <!-- Guest Detail removed — now a separate page -->
  </div>
</template>
