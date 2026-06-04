<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator } from '@/components/ui/dropdown-menu'
import { reservationsApi, type Reservation, type ReservationStatus } from '@/api/reservations'
import { receptionApi, type Room } from '@/api/reception'
import { useToastStore } from '@/stores/toast'
import { useWsStore } from '@/stores/ws'
import { parseApiError } from '@/composables/useOptimistic'
import { Plus, Check, UserCheck, X, UserX, Loader2, MoreVertical, LogOut, Copy, Check as CheckIcon } from 'lucide-vue-next'
import { Skeleton } from '@/components/ui/skeleton'

const items = ref<Reservation[]>([])
const roomsList = ref<Room[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const filter = ref('all')

const toast = useToastStore()
const ws = useWsStore()

const createOpen = ref(false)
const cancelDialogOpen = ref(false)

// Credentials dialog (shown after check-in)
const credentialsOpen = ref(false)
const credentials = ref<{ guest_login: string; guest_pin: string; room_number: number; full_name: string } | null>(null)
const copied = ref(false)

function copyCredentials() {
  if (!credentials.value) return
  navigator.clipboard.writeText(`Login: ${credentials.value.guest_login}\nPIN: ${credentials.value.guest_pin}`)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}
const toCancel = ref<Reservation | null>(null)

const draft = ref({
  full_name: '',
  phone: '',
  passport_number: '',
  room_id: '',
  check_in_date: '',
  check_out_date: ''
})
const submitting = ref(false)

const STATUS_LABELS: Record<ReservationStatus, string> = {
  pending: 'Kutilmoqda',
  confirmed: 'Tasdiqlangan',
  checked_in: 'Qabul qilingan',
  cancelled: 'Bekor qilingan',
  no_show: 'Kelmadi'
}

function statusVariant(status: ReservationStatus): 'default' | 'success' | 'warning' | 'destructive' | 'secondary' {
  if (status === 'confirmed') return 'success'
  if (status === 'pending') return 'warning'
  if (status === 'checked_in') return 'default'
  if (status === 'cancelled' || status === 'no_show') return 'destructive'
  return 'secondary'
}

const visible = computed(() =>
  filter.value === 'all' ? items.value : items.value.filter((r) => r.status === filter.value)
)

function money(minor: number) { return (minor / 100).toLocaleString('uz-UZ') + " so'm" }

function nights(r: Reservation) {
  const ms = new Date(r.check_out_date).getTime() - new Date(r.check_in_date).getTime()
  return Math.max(1, Math.round(ms / 86400000))
}

async function load() {
  loading.value = true
  try {
    const [rs, rms] = await Promise.all([reservationsApi.list(), receptionApi.listRooms()])
    items.value = rs
    roomsList.value = rms.rooms
  } catch (e: unknown) {
    error.value = parseApiError(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)

watch(
  () => ws.lastEvent,
  (env) => { if (env?.channel?.startsWith('reservations.')) load() }
)

function openCreate() {
  const today = new Date().toISOString().slice(0, 10)
  const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10)
  draft.value = { full_name: '', phone: '', passport_number: '', room_id: '', check_in_date: today, check_out_date: tomorrow }
  createOpen.value = true
}

async function submitCreate() {
  submitting.value = true
  try {
    const created = await reservationsApi.create({
      full_name: draft.value.full_name.trim(),
      phone: draft.value.phone.trim(),
      passport_number: draft.value.passport_number.trim() || undefined,
      room_id: draft.value.room_id,
      check_in_date: draft.value.check_in_date,
      check_out_date: draft.value.check_out_date
    })
    items.value = [created, ...items.value]
    toast.success(`#${created.room_number}-xona uchun bron yaratildi`)
    createOpen.value = false
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: { error?: string } } } }
    const code = err.response?.data?.detail?.error
    if (code === 'room_unavailable_for_dates') {
      toast.error("Bu xona tanlangan sanalar uchun band — boshqa xona yoki sana tanlang.")
    } else {
      toast.error(parseApiError(e))
    }
  } finally {
    submitting.value = false
  }
}

async function confirm(r: Reservation) {
  try {
    const updated = await reservationsApi.confirm(r.id)
    Object.assign(r, updated)
    toast.success('Bron tasdiqlandi')
  } catch (e) { toast.error(parseApiError(e)) }
}

async function noShow(r: Reservation) {
  try {
    const updated = await reservationsApi.noShow(r.id)
    Object.assign(r, updated)
    toast.info('Mehmon kelmadi deb belgilandi')
  } catch (e) { toast.error(parseApiError(e)) }
}

async function checkIn(r: Reservation) {
  try {
    const result = await reservationsApi.checkIn(r.id)
    toast.success(`Mehmon #${r.room_number}-xonaga joylashtirildi`)
    credentials.value = result
    credentialsOpen.value = true
    await load()
  } catch (e) { toast.error(parseApiError(e)) }
}

async function checkOut(r: Reservation) {
  if (!r.guest_id) { toast.error('Mehmon topilmadi'); return }
  try {
    await receptionApi.checkOut(r.guest_id)
    toast.success(`Mehmon #${r.room_number}-xonadan jo'natildi`)
    await load()
  } catch (e) { toast.error(parseApiError(e)) }
}

function askCancel(r: Reservation) {
  toCancel.value = r
  cancelDialogOpen.value = true
}

async function doCancel() {
  if (!toCancel.value) return
  try {
    const updated = await reservationsApi.cancel(toCancel.value.id)
    Object.assign(toCancel.value, updated)
    toast.info('Bron bekor qilindi')
  } catch (e) { toast.error(parseApiError(e)) }
  finally {
    toCancel.value = null
    cancelDialogOpen.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Filters -->
    <Card>
      <CardContent class="p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <Select v-model="filter">
          <SelectTrigger class="w-[180px]">
            <SelectValue placeholder="Holat" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Barcha holatlar</SelectItem>
            <SelectItem value="pending">Kutilmoqda</SelectItem>
            <SelectItem value="confirmed">Tasdiqlangan</SelectItem>
            <SelectItem value="checked_in">Qabul qilingan</SelectItem>
            <SelectItem value="cancelled">Bekor qilingan</SelectItem>
            <SelectItem value="no_show">Kelmadi</SelectItem>
          </SelectContent>
        </Select>
        <Button size="sm" @click="openCreate">
          <Plus class="w-4 h-4 mr-1" />
          Yangi bron
        </Button>
      </CardContent>
    </Card>

    <!-- States -->
    <div v-if="error" class="rounded-md bg-destructive/10 text-destructive text-sm p-4">{{ error }}</div>
    <div v-if="loading" class="space-y-3">
      <Card>
        <div class="p-4 space-y-4">
          <div v-for="i in 5" :key="i" class="flex items-center gap-4">
            <Skeleton class="h-4 w-24" />
            <Skeleton class="h-4 w-28" />
            <Skeleton class="h-4 w-16" />
            <Skeleton class="h-4 w-20" />
            <Skeleton class="h-4 w-20" />
            <Skeleton class="h-4 w-10" />
            <Skeleton class="h-5 w-20 rounded-full" />
          </div>
        </div>
      </Card>
    </div>
    <div v-else-if="!visible.length" class="text-center py-12 text-muted-foreground">Bronlar topilmadi.</div>

    <!-- Table -->
    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Mehmon</TableHead>
            <TableHead>Telefon</TableHead>
            <TableHead>Xona</TableHead>
            <TableHead>Kirish</TableHead>
            <TableHead>Chiqish</TableHead>
            <TableHead class="text-right">Tunlar</TableHead>
            <TableHead class="text-right">Tunlik</TableHead>
            <TableHead>Status</TableHead>
            <TableHead class="text-right">Harakat</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="r in visible" :key="r.id">
            <TableCell class="font-medium">{{ r.full_name }}</TableCell>
            <TableCell class="text-muted-foreground font-mono text-xs">{{ r.phone }}</TableCell>
            <TableCell class="font-mono">#{{ r.room_number }} <span class="text-muted-foreground">/ {{ r.floor }}q</span></TableCell>
            <TableCell>{{ new Date(r.check_in_date).toLocaleDateString('uz-UZ') }}</TableCell>
            <TableCell>{{ new Date(r.check_out_date).toLocaleDateString('uz-UZ') }}</TableCell>
            <TableCell class="text-right tabular-nums">{{ nights(r) }}</TableCell>
            <TableCell class="text-right font-mono tabular-nums">{{ money(r.nightly_rate_locked_minor_units) }}</TableCell>
            <TableCell>
              <Badge :variant="statusVariant(r.status)">{{ STATUS_LABELS[r.status] }}</Badge>
            </TableCell>
            <TableCell class="text-right">
              <DropdownMenu>
                <DropdownMenuTrigger as-child>
                  <Button variant="ghost" size="icon-sm">
                    <MoreVertical class="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem v-if="r.status === 'pending'" @click="confirm(r)">
                    <Check class="w-4 h-4 mr-2" />
                    Tasdiqlash
                  </DropdownMenuItem>
                  <DropdownMenuItem v-if="r.status === 'pending' || r.status === 'confirmed'" @click="checkIn(r)">
                    <UserCheck class="w-4 h-4 mr-2" />
                    Check-in
                  </DropdownMenuItem>
                  <DropdownMenuItem v-if="r.status === 'checked_in'" @click="checkOut(r)">
                    <LogOut class="w-4 h-4 mr-2" />
                    Check-out
                  </DropdownMenuItem>
                  <DropdownMenuSeparator v-if="r.status === 'pending' || r.status === 'confirmed'" />
                  <DropdownMenuItem v-if="r.status === 'pending' || r.status === 'confirmed'" @click="noShow(r)">
                    <UserX class="w-4 h-4 mr-2" />
                    Kelmadi
                  </DropdownMenuItem>
                  <DropdownMenuItem v-if="r.status === 'pending' || r.status === 'confirmed'" class="text-destructive focus:text-destructive" @click="askCancel(r)">
                    <X class="w-4 h-4 mr-2" />
                    Bekor qilish
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>

    <!-- Create Dialog -->
    <Dialog :open="createOpen" @update:open="createOpen = $event">
      <DialogContent class="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Yangi bron yaratish</DialogTitle>
        </DialogHeader>
        <form @submit.prevent="submitCreate" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label>To'liq ism</Label>
              <Input v-model="draft.full_name" required />
            </div>
            <div class="space-y-2">
              <Label>Telefon</Label>
              <Input v-model="draft.phone" type="tel" placeholder="+998901234567" required />
            </div>
          </div>
          <div class="space-y-2">
            <Label>Pasport (ixtiyoriy)</Label>
            <Input v-model="draft.passport_number" />
          </div>
          <div class="space-y-2">
            <Label>Xona</Label>
            <Select v-model="draft.room_id">
              <SelectTrigger>
                <SelectValue placeholder="Xonani tanlang" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="r in roomsList" :key="r.id" :value="r.id">
                  #{{ r.room_number }} — {{ r.room_type }} ({{ r.floor }}q, {{ money(r.nightly_rate_minor_units) }}/tun)
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label>Kirish sanasi</Label>
              <Input v-model="draft.check_in_date" type="date" required />
            </div>
            <div class="space-y-2">
              <Label>Chiqish sanasi</Label>
              <Input v-model="draft.check_out_date" type="date" required />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" type="button" :disabled="submitting" @click="createOpen = false">Bekor</Button>
            <Button type="submit" :disabled="submitting">
              <Loader2 v-if="submitting" class="w-4 h-4 mr-2 animate-spin" />
              Bron qilish
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>

    <!-- Cancel Confirmation -->
    <Dialog :open="cancelDialogOpen" @update:open="cancelDialogOpen = $event">
      <DialogContent class="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>{{ toCancel ? `${toCancel.full_name} bronini bekor qilish?` : '' }}</DialogTitle>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" @click="cancelDialogOpen = false; toCancel = null">Yopish</Button>
          <Button variant="destructive" @click="doCancel">Bekor qilish</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Credentials Dialog (after check-in) -->
    <Dialog :open="credentialsOpen" @update:open="credentialsOpen = $event">
      <DialogContent class="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Mehmon kirish ma'lumotlari</DialogTitle>
        </DialogHeader>
        <div v-if="credentials" class="space-y-4">
          <div class="rounded-lg bg-success/10 border border-success/20 p-3 text-center">
            <p class="text-green-700 font-medium text-sm">{{ credentials.full_name }} muvaffaqiyatli joylashtirildi</p>
            <p class="text-xs text-muted-foreground">Xona #{{ credentials.room_number }}</p>
          </div>
          <div class="grid grid-cols-2 gap-3 p-3 border rounded-lg">
            <div>
              <p class="text-xs text-muted-foreground">Login</p>
              <p class="font-mono font-semibold text-sm">{{ credentials.guest_login }}</p>
            </div>
            <div>
              <p class="text-xs text-muted-foreground">PIN</p>
              <p class="font-mono font-bold text-xl text-primary tracking-widest">{{ credentials.guest_pin }}</p>
            </div>
          </div>
          <Button variant="outline" size="sm" class="w-full" @click="copyCredentials">
            <component :is="copied ? CheckIcon : Copy" class="w-4 h-4 mr-2" />
            {{ copied ? 'Nusxalandi!' : 'Nusxalash' }}
          </Button>
          <p class="text-xs text-muted-foreground text-center">Bu ma'lumotlar mehmon portaliga kirish uchun</p>
        </div>
        <DialogFooter>
          <Button @click="credentialsOpen = false">Yopish</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
