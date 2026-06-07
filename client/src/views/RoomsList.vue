<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator } from '@/components/ui/dropdown-menu'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import CheckInForm from './CheckInForm.vue'
import RoomDetail from './RoomDetail.vue'
import { receptionApi, type Proximity, type Room, type RoomType } from '@/api/reception'
import { useRoomsStore } from '@/stores/rooms'
import { useMaintenanceStore } from '@/stores/maintenance'
import { useWsStore } from '@/stores/ws'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { parseApiError } from '@/composables/useOptimistic'
import { cn } from '@/lib/utils'
import {
  MoreVertical,
  Plus,
  Layers,
  Eye,
  Pencil,
  Trash2,
  BedDouble,
  Users,
  Sparkles,
  Wrench as WrenchIcon,
  Loader2,
} from 'lucide-vue-next'

const rooms = useRoomsStore()
const maintenance = useMaintenanceStore()
const ws = useWsStore()
const auth = useAuthStore()
const toast = useToastStore()

const isManager = computed(() => auth.role === 'manager')
const canCheckIn = computed(() => auth.role === 'manager' || auth.role === 'reception')

const editorOpen = ref(false)
const editorMode = ref<'new' | 'edit'>('new')
const editorRoom = ref<Room | null>(null)
const saving = ref(false)

const deleteDialogOpen = ref(false)
const toDelete = ref<Room | null>(null)
const deleteConfirmed = ref(false)
const deleteWarning = ref('')

const detailRoom = ref<Room | null>(null)
const checkInOpen = ref(false)
const checkInRoom = ref<Room | null>(null)

const draft = ref({
  room_number: 0,
  floor: '1',
  room_type: 'double' as RoomType,
  proximity: 'elevator' as Proximity,
  price_som: 200000
})

// Bulk create state
const editorTab = ref<'single' | 'bulk'>('single')
const bulkSaving = ref(false)
const bulkFloor = ref(1)
const bulkStart = ref(101)
const bulkEnd = ref(110)
const bulkStep = ref<'setup' | 'configure'>('setup')
const bulkDefaultPrices = ref<Record<RoomType, number>>({
  single: 200000,
  double: 350000,
  suite: 800000,
  accessible: 250000,
})

interface BulkRoom {
  room_number: number
  room_type: RoomType | null
  proximity: Proximity
  price_som: number
  exists: boolean
}
const bulkRooms = ref<BulkRoom[]>([])
const bulkActiveType = ref<RoomType>('single')

function generateBulkRooms() {
  if (bulkStart.value <= 0 || bulkEnd.value < bulkStart.value) {
    toast.error("Oraliq noto'g'ri")
    return
  }
  if (bulkEnd.value - bulkStart.value > 50) {
    toast.error("Bir martada maksimal 50 ta xona")
    return
  }
  const existingNumbers = new Set(rooms.rooms.map(r => r.room_number))
  const arr: BulkRoom[] = []
  for (let num = bulkStart.value; num <= bulkEnd.value; num++) {
    arr.push({
      room_number: num,
      room_type: null,
      proximity: 'elevator',
      price_som: 0,
      exists: existingNumbers.has(num),
    })
  }
  bulkRooms.value = arr
  bulkStep.value = 'configure'
}

function assignBulkType(idx: number) {
  const room = bulkRooms.value[idx]
  if (room.exists) return
  if (room.room_type === bulkActiveType.value) {
    // Same type — un-assign
    room.room_type = null
    room.price_som = 0
  } else {
    // Assign (or reassign from different type)
    room.room_type = bulkActiveType.value
    room.price_som = bulkDefaultPrices.value[bulkActiveType.value]
  }
}

function toggleBulkProximity(idx: number) {
  const room = bulkRooms.value[idx]
  if (room.exists) return
  const cycle: Proximity[] = ['elevator', 'stairs', 'other']
  const cur = cycle.indexOf(room.proximity)
  room.proximity = cycle[(cur + 1) % cycle.length]
}

const PROX_SHORT: Record<string, string> = { elevator: 'Lift', stairs: 'Zina', other: 'Boshqa' }

const bulkReady = computed(() => bulkRooms.value.filter(r => !r.exists && r.room_type !== null))
const bulkUnassigned = computed(() => bulkRooms.value.filter(r => !r.exists && r.room_type === null))
const bulkByType = computed(() => {
  const map: Record<RoomType, BulkRoom[]> = { single: [], double: [], suite: [], accessible: [] }
  for (const r of bulkRooms.value) {
    if (!r.exists && r.room_type) map[r.room_type].push(r)
  }
  return map
})

async function saveBulk() {
  if (!bulkReady.value.length) {
    toast.error("Kamida bitta xonaga tur belgilang")
    return
  }
  bulkSaving.value = true
  try {
    const payload = bulkReady.value.map(r => ({
      room_number: r.room_number,
      floor: bulkFloor.value,
      room_type: r.room_type!,
      proximity: r.proximity,
      nightly_rate_minor_units: Math.round(r.price_som * 100)
    }))
    await receptionApi.createRoomsBulk({ rooms: payload })
    toast.success(`${payload.length} ta xona muvaffaqiyatli qo'shildi`)
    editorOpen.value = false
    bulkStep.value = 'setup'
    bulkRooms.value = []
    await rooms.load()
  } catch (e: unknown) {
    toast.error(parseApiError(e))
  } finally {
    bulkSaving.value = false
  }
}

const filterStatus = ref('all')
const filterType = ref('all')

const statusFilters = [
  { v: 'all', l: 'Barchasi' },
  { v: 'available', l: "Bo'sh" },
  { v: 'occupied', l: 'Band' },
  { v: 'out_of_service', l: 'Xizmatdan tashqari' },
]

const TYPE_UZ: Record<string, string> = {
  single: 'Bir kishilik',
  double: 'Ikki kishilik',
  suite: 'Lyuks',
  accessible: 'Nogironlar uchun'
}

const STATUS_UZ: Record<string, string> = {
  available: "Bo'sh",
  occupied: 'Band',
  out_of_service: 'Xizmatdan tashqari'
}

const CLEANLINESS_UZ: Record<string, string> = {
  clean: 'Toza',
  dirty: 'Iflos',
  cleaning: 'Tozalanmoqda',
  maintenance: 'Nosozlik'
}

const visible = computed(() =>
  rooms.rooms.filter((r) => {
    if (filterStatus.value !== 'all' && r.status !== filterStatus.value) return false
    if (filterType.value !== 'all' && r.room_type !== filterType.value) return false
    return true
  })
)

const counts = computed(() => {
  const total = rooms.rooms.length
  const available = rooms.rooms.filter((r) => r.status === 'available' && r.cleanliness_status === 'clean').length
  const occupied = rooms.rooms.filter((r) => r.status === 'occupied').length
  const cleaning = rooms.rooms.filter((r) => r.cleanliness_status === 'cleaning').length
  const maintenance = rooms.rooms.filter((r) => r.cleanliness_status === 'maintenance').length
  return { total, available, occupied, cleaning, maintenance }
})

onMounted(() => {
  rooms.load()
  if (auth.role !== 'kitchen' && auth.role !== 'cleaner') {
    maintenance.load(auth.role || undefined)
  }
})

watch(
  () => ws.lastEvent,
  (env) => {
    const ch = env?.channel ?? ''
    if (ch.startsWith('rooms.') || ch.startsWith('guests.')) rooms.load()
  }
)

function isAssignable(r: Room) {
  return r.status === 'available' && r.cleanliness_status === 'clean'
}

function maintenanceStatus(r: Room): string | null {
  if (r.cleanliness_status !== 'maintenance') return null
  const issue = maintenance.open.find(i => i.room_id === r.id)
  if (!issue) return 'Nosozlik'
  if (issue.status === 'reported') return 'Tayinlanmagan'
  if (issue.status === 'assigned') return 'Tayinlangan'
  return 'Nosozlik'
}

function money(minor: number) { return (minor / 100).toLocaleString('uz-UZ') + " so'm" }

function statusVariant(status: string): 'success' | 'default' | 'destructive' | 'warning' | 'secondary' {
  if (status === 'available' || status === 'clean') return 'success'
  if (status === 'occupied') return 'default'
  if (status === 'maintenance' || status === 'out_of_service') return 'destructive'
  if (status === 'dirty' || status === 'cleaning') return 'warning'
  return 'secondary'
}

function openEditor(target: Room | 'new') {
  if (target === 'new') {
    editorMode.value = 'new'
    editorRoom.value = null
    editorTab.value = 'single'
    bulkStep.value = 'setup'
    bulkRooms.value = []
    draft.value = { room_number: 0, floor: '1', room_type: 'double', proximity: 'elevator', price_som: 200000 }
  } else {
    editorMode.value = 'edit'
    editorRoom.value = target
    draft.value = {
      room_number: target.room_number,
      floor: String(target.floor),
      room_type: target.room_type,
      proximity: target.proximity,
      price_som: target.nightly_rate_minor_units / 100
    }
  }
  editorOpen.value = true
}

async function saveDraft() {
  saving.value = true
  try {
    const ratePayload = Math.round(draft.value.price_som * 100)
    if (editorMode.value === 'new') {
      await receptionApi.createRoom({
        room_number: draft.value.room_number,
        floor: Number(draft.value.floor),
        room_type: draft.value.room_type,
        proximity: draft.value.proximity,
        nightly_rate_minor_units: ratePayload
      })
      toast.success(`#${draft.value.room_number}-xona qo'shildi`)
    } else if (editorRoom.value) {
      await receptionApi.updateRoom(editorRoom.value.id, {
        floor: Number(draft.value.floor),
        room_type: draft.value.room_type,
        proximity: draft.value.proximity,
        nightly_rate_minor_units: ratePayload
      })
      toast.success('Xona yangilandi')
    }
    editorOpen.value = false
    await rooms.load()
  } catch (e: unknown) {
    toast.error(parseApiError(e))
  } finally {
    saving.value = false
  }
}

function askDelete(r: Room) {
  toDelete.value = r
  deleteConfirmed.value = false
  deleteWarning.value = ''
  deleteDialogOpen.value = true
}

async function confirmDelete() {
  if (!toDelete.value) return
  try {
    await receptionApi.deleteRoom(toDelete.value.id, deleteConfirmed.value)
    toast.info("Xona o'chirildi")
    deleteDialogOpen.value = false
    await rooms.load()
    deleteConfirmed.value = false
    deleteWarning.value = ''
  } catch (e: any) {
    const detail = e?.response?.data
    if (detail?.requires_confirmation && !deleteConfirmed.value) {
      deleteWarning.value = detail.message
      deleteConfirmed.value = true
      return
    }
    toast.error(parseApiError(e))
    deleteDialogOpen.value = false
    deleteConfirmed.value = false
    deleteWarning.value = ''
  } finally {
    if (!deleteConfirmed.value) toDelete.value = null
  }
}

function openCheckInForRoom(r: Room) {
  if (!canCheckIn.value) return
  if (r.status === 'occupied') {
    toast.info(`#${r.room_number} band — avval mehmonni chiqaring`)
    return
  }
  if (r.status === 'out_of_service') {
    toast.info(`#${r.room_number} xizmatdan tashqari`)
    return
  }
  if (r.cleanliness_status !== 'clean') {
    toast.info(`#${r.room_number} hali tozalanmagan (${CLEANLINESS_UZ[r.cleanliness_status] || r.cleanliness_status})`)
    return
  }
  checkInRoom.value = r
  checkInOpen.value = true
}

function openCheckInGeneral() {
  checkInRoom.value = null
  checkInOpen.value = true
}

function onCheckInSuccess() {
  checkInOpen.value = false
  checkInRoom.value = null
  rooms.load()
}
</script>

<template>
  <div class="space-y-6">
    <!-- Stat cards -->
    <div class="grid grid-cols-2 sm:grid-cols-5 gap-3">
      <template v-if="rooms.loading && !rooms.rooms.length">
        <Card v-for="i in 5" :key="i">
          <CardContent class="p-3 text-center space-y-1">
            <Skeleton class="h-6 w-8 mx-auto" />
            <Skeleton class="h-3 w-14 mx-auto" />
          </CardContent>
        </Card>
      </template>
      <template v-else>
        <Card class="h-20 flex items-center justify-center">
          <div class="text-center">
            <p class="text-xl font-bold tracking-tighter tabular-nums">{{ counts.total }}</p>
            <p class="text-[11px] uppercase text-muted-foreground tracking-wider">Jami</p>
          </div>
        </Card>
        <Card class="h-20 flex items-center justify-center">
          <div class="text-center">
            <p class="text-xl font-bold tracking-tighter tabular-nums text-green-600">{{ counts.available }}</p>
            <p class="text-[11px] uppercase text-muted-foreground tracking-wider">Bo'sh</p>
          </div>
        </Card>
        <Card class="h-20 flex items-center justify-center">
          <div class="text-center">
            <p class="text-xl font-bold tracking-tighter tabular-nums text-primary">{{ counts.occupied }}</p>
            <p class="text-[11px] uppercase text-muted-foreground tracking-wider">Band</p>
          </div>
        </Card>
        <Card class="h-20 flex items-center justify-center">
          <div class="text-center">
            <p class="text-xl font-bold tracking-tighter tabular-nums text-amber-600">{{ counts.cleaning }}</p>
            <p class="text-[11px] uppercase text-muted-foreground tracking-wider">Tozalanmoqda</p>
          </div>
        </Card>
        <Card class="h-20 flex items-center justify-center">
          <div class="text-center">
            <p class="text-xl font-bold tracking-tighter tabular-nums text-destructive">{{ counts.maintenance }}</p>
            <p class="text-[11px] uppercase text-muted-foreground tracking-wider">Texnik</p>
          </div>
        </Card>
      </template>
    </div>

    <!-- Filters + actions -->
    <Card>
      <CardContent class="p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div class="flex gap-3">
          <Select v-model="filterStatus">
            <SelectTrigger class="w-[180px]">
              <SelectValue placeholder="Holat" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Barcha holatlar</SelectItem>
              <SelectItem value="available">Bo'sh</SelectItem>
              <SelectItem value="occupied">Band</SelectItem>
              <SelectItem value="out_of_service">Xizmatdan tashqari</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="flex gap-2">
          <Button v-if="isManager" variant="outline" size="sm" @click="openEditor('new')">
            <Plus class="w-4 h-4 mr-1" />
            Xona qo'shish
          </Button>
          <Button v-if="canCheckIn" size="sm" @click="openCheckInGeneral">
            <Users class="w-4 h-4 mr-1" />
            Band qilish
          </Button>
        </div>
      </CardContent>
    </Card>

    <!-- Loading / error states -->
    <div v-if="rooms.error" class="rounded-md bg-destructive/10 text-destructive text-sm p-4">
      {{ rooms.error }}
    </div>
    <div v-if="rooms.loading && !rooms.rooms.length" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <Card v-for="i in 8" :key="i">
        <CardContent class="p-4 space-y-3">
          <div class="flex items-start justify-between">
            <div class="space-y-2">
              <Skeleton class="h-6 w-16" />
              <Skeleton class="h-4 w-24" />
            </div>
            <Skeleton class="h-5 w-12 rounded-full" />
          </div>
          <div class="flex gap-1.5">
            <Skeleton class="h-5 w-10 rounded-full" />
            <Skeleton class="h-5 w-20 rounded-full" />
            <Skeleton class="h-5 w-14 rounded-full" />
          </div>
          <Skeleton class="h-1.5 w-full rounded-full" />
        </CardContent>
      </Card>
    </div>
    <div v-else-if="!visible.length" class="text-center py-12 text-muted-foreground">
      Filtrlarga mos xona topilmadi.
    </div>

    <!-- Room cards grid -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <Card
        v-for="r in visible"
        :key="r.id"
        :class="cn(
          'transition-all duration-200 border-l-2',
          r.status === 'available' && r.cleanliness_status === 'clean' ? 'border-l-green-500' :
          r.status === 'occupied' ? 'border-l-blue-500' :
          r.cleanliness_status === 'cleaning' ? 'border-l-amber-400' :
          r.cleanliness_status === 'maintenance' || r.status === 'out_of_service' ? 'border-l-red-500' :
          'border-l-muted',
          canCheckIn && 'cursor-pointer',
          canCheckIn && isAssignable(r) && 'hover:shadow-md hover:border-primary/30 hover:-translate-y-0.5'
        )"
        @click="openCheckInForRoom(r)"
      >
        <CardContent class="p-4 space-y-3">
          <div class="flex items-start justify-between">
            <div>
              <p class="text-xl font-bold tracking-tight">#{{ r.room_number }}</p>
              <p class="text-sm text-muted-foreground tabular-nums">{{ money(r.dynamic_price_minor_units || r.nightly_rate_minor_units) }}/tun</p>
            </div>
            <div class="flex items-center gap-2">
              <Badge :variant="statusVariant(r.status)">{{ STATUS_UZ[r.status] || r.status }}</Badge>
              <DropdownMenu v-if="isManager">
                <DropdownMenuTrigger as-child>
                  <Button variant="ghost" size="icon-sm" @click.stop>
                    <MoreVertical class="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem @click.stop="detailRoom = r">
                    <Eye class="w-4 h-4 mr-2" />
                    Batafsil
                  </DropdownMenuItem>
                  <DropdownMenuItem @click.stop="openEditor(r)">
                    <Pencil class="w-4 h-4 mr-2" />
                    Tahrirlash
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem class="text-destructive focus:text-destructive" @click.stop="askDelete(r)">
                    <Trash2 class="w-4 h-4 mr-2" />
                    O'chirish
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
          <div class="flex flex-wrap gap-1.5">
            <Badge variant="secondary" class="text-xs">{{ r.floor }}q</Badge>
            <Badge variant="secondary" class="text-xs">{{ TYPE_UZ[r.room_type] || r.room_type }}</Badge>
            <Badge :variant="statusVariant(r.cleanliness_status)" class="text-xs">{{ CLEANLINESS_UZ[r.cleanliness_status] || r.cleanliness_status }}</Badge>
          </div>
          <!-- Freshness bar -->
          <div class="w-full h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all"
              :class="r.freshness_score > 0.6 ? 'bg-green-500' : r.freshness_score > 0.3 ? 'bg-amber-400' : 'bg-red-500'"
              :style="{ width: (r.freshness_score * 100) + '%' }"
            />
          </div>
          <p v-if="canCheckIn && isAssignable(r)" class="text-xs font-medium text-primary">
            Mehmon qabul qilish →
          </p>
          <p v-else-if="canCheckIn && r.status === 'occupied'" class="text-xs font-medium text-blue-600">
            Band
          </p>
          <p v-else-if="canCheckIn && r.status === 'available' && r.cleanliness_status === 'maintenance'" class="text-xs font-medium" :class="maintenanceStatus(r) === 'Tayinlanmagan' ? 'text-red-600' : 'text-amber-600'">
            🔧 {{ maintenanceStatus(r) }}
          </p>
          <p v-else-if="canCheckIn && r.status === 'available' && r.cleanliness_status !== 'clean'" class="text-xs font-medium text-amber-600">
            {{ CLEANLINESS_UZ[r.cleanliness_status] || r.cleanliness_status }}
          </p>
        </CardContent>
      </Card>
    </div>

    <!-- Editor Dialog -->
    <Dialog :open="editorOpen" @update:open="editorOpen = $event">
      <DialogContent :class="editorMode === 'new' && editorTab === 'bulk' ? 'sm:max-w-3xl max-h-[90vh] overflow-y-auto' : 'sm:max-w-lg'">
        <DialogHeader>
          <DialogTitle>{{ editorMode === 'edit' ? 'Xonani tahrirlash' : 'Xona qo\'shish' }}</DialogTitle>
        </DialogHeader>

        <!-- Edit mode — no tabs -->
        <form v-if="editorMode === 'edit'" @submit.prevent="saveDraft" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label>Qavat</Label>
              <Select v-model="draft.floor">
                <SelectTrigger>
                  <SelectValue placeholder="Qavat" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1-qavat</SelectItem>
                  <SelectItem value="2">2-qavat</SelectItem>
                  <SelectItem value="3">3-qavat</SelectItem>
                  <SelectItem value="4">4-qavat</SelectItem>
                  <SelectItem value="5">5-qavat</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="space-y-2">
              <Label>Tunlik narx (so'm)</Label>
              <Input v-model.number="draft.price_som" type="number" min="1" required />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label>Turi</Label>
              <Select v-model="draft.room_type">
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="single">Bir kishilik</SelectItem>
                  <SelectItem value="double">Ikki kishilik</SelectItem>
                  <SelectItem value="suite">Lyuks</SelectItem>
                  <SelectItem value="accessible">Nogironlar uchun</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="space-y-2">
              <Label>Joylashuv</Label>
              <Select v-model="draft.proximity">
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="elevator">Lift yonida</SelectItem>
                  <SelectItem value="stairs">Zinapoya yonida</SelectItem>
                  <SelectItem value="other">Boshqa</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" type="button" @click="editorOpen = false" :disabled="saving">Bekor</Button>
            <Button type="submit" :disabled="saving">
              <Loader2 v-if="saving" class="w-4 h-4 mr-2 animate-spin" />
              Saqlash
            </Button>
          </DialogFooter>
        </form>

        <!-- New mode — tabs: bitta / ko'p -->
        <Tabs v-else v-model="editorTab" class="mt-2">
          <TabsList class="w-full">
            <TabsTrigger value="single" class="flex-1">Bitta xona</TabsTrigger>
            <TabsTrigger value="bulk" class="flex-1">Ko'p xona</TabsTrigger>
          </TabsList>

          <!-- Single room tab -->
          <TabsContent value="single">
            <form @submit.prevent="saveDraft" class="space-y-4 pt-2">
              <div class="space-y-2">
                <Label>Xona raqami</Label>
                <Input v-model.number="draft.room_number" type="number" min="1" max="9999" required />
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div class="space-y-2">
                  <Label>Qavat</Label>
                  <Select v-model="draft.floor">
                    <SelectTrigger><SelectValue placeholder="Qavat" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1-qavat</SelectItem>
                      <SelectItem value="2">2-qavat</SelectItem>
                      <SelectItem value="3">3-qavat</SelectItem>
                      <SelectItem value="4">4-qavat</SelectItem>
                      <SelectItem value="5">5-qavat</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div class="space-y-2">
                  <Label>Tunlik narx (so'm)</Label>
                  <Input v-model.number="draft.price_som" type="number" min="1" required />
                </div>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div class="space-y-2">
                  <Label>Turi</Label>
                  <Select v-model="draft.room_type">
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="single">Bir kishilik</SelectItem>
                      <SelectItem value="double">Ikki kishilik</SelectItem>
                      <SelectItem value="suite">Lyuks</SelectItem>
                      <SelectItem value="accessible">Nogironlar uchun</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div class="space-y-2">
                  <Label>Joylashuv</Label>
                  <Select v-model="draft.proximity">
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="elevator">Lift yonida</SelectItem>
                      <SelectItem value="stairs">Zinapoya yonida</SelectItem>
                      <SelectItem value="other">Boshqa</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" type="button" @click="editorOpen = false" :disabled="saving">Bekor</Button>
                <Button type="submit" :disabled="saving">
                  <Loader2 v-if="saving" class="w-4 h-4 mr-2 animate-spin" />
                  Qo'shish
                </Button>
              </DialogFooter>
            </form>
          </TabsContent>

          <!-- Bulk room tab -->
          <TabsContent value="bulk">
            <!-- Step 1: Setup range + default prices -->
            <div v-if="bulkStep === 'setup'" class="space-y-4 pt-2">
              <div class="grid grid-cols-3 gap-3">
                <div class="space-y-2">
                  <Label>Qavat</Label>
                  <Input v-model.number="bulkFloor" type="number" min="1" max="99" required />
                </div>
                <div class="space-y-2">
                  <Label>Dan (raqam)</Label>
                  <Input v-model.number="bulkStart" type="number" min="1" max="9999" required />
                </div>
                <div class="space-y-2">
                  <Label>Gacha (raqam)</Label>
                  <Input v-model.number="bulkEnd" type="number" min="1" max="9999" required />
                </div>
              </div>

              <div class="border-t pt-3 space-y-3">
                <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Default narxlar (so'm/tun)</p>
                <div class="grid grid-cols-2 gap-3">
                  <div class="space-y-1">
                    <Label class="text-xs">Bir kishilik</Label>
                    <Input v-model.number="bulkDefaultPrices.single" type="number" min="1" />
                  </div>
                  <div class="space-y-1">
                    <Label class="text-xs">Ikki kishilik</Label>
                    <Input v-model.number="bulkDefaultPrices.double" type="number" min="1" />
                  </div>
                  <div class="space-y-1">
                    <Label class="text-xs">Lyuks</Label>
                    <Input v-model.number="bulkDefaultPrices.suite" type="number" min="1" />
                  </div>
                  <div class="space-y-1">
                    <Label class="text-xs">Nogironlar uchun</Label>
                    <Input v-model.number="bulkDefaultPrices.accessible" type="number" min="1" />
                  </div>
                </div>
              </div>

              <p class="text-xs text-muted-foreground">
                {{ bulkEnd >= bulkStart ? `${bulkEnd - bulkStart + 1} ta xona generatsiya qilinadi` : "Oraliq noto'g'ri" }}
              </p>
              <DialogFooter>
                <Button variant="outline" type="button" @click="editorOpen = false">Bekor</Button>
                <Button :disabled="bulkEnd < bulkStart" @click="generateBulkRooms">
                  Keyingi →
                </Button>
              </DialogFooter>
            </div>

            <!-- Step 2: Configure rooms with type tabs -->
            <div v-else class="space-y-4 pt-2">
              <div class="flex items-center justify-between">
                <Button variant="ghost" size="sm" @click="bulkStep = 'setup'">← Orqaga</Button>
                <span class="text-xs text-muted-foreground">{{ bulkFloor }}-qavat · {{ bulkRooms.filter(r => !r.exists).length }} yangi</span>
              </div>

              <!-- Type tabs at top -->
              <Tabs v-model="bulkActiveType">
                <TabsList class="w-full">
                  <TabsTrigger value="single" class="flex-1 text-xs gap-1">
                    Bir kishilik
                    <Badge variant="secondary" class="text-[10px] px-1">{{ bulkByType.single.length }}</Badge>
                  </TabsTrigger>
                  <TabsTrigger value="double" class="flex-1 text-xs gap-1">
                    Ikki kishilik
                    <Badge variant="secondary" class="text-[10px] px-1">{{ bulkByType.double.length }}</Badge>
                  </TabsTrigger>
                  <TabsTrigger value="suite" class="flex-1 text-xs gap-1">
                    Lyuks
                    <Badge variant="secondary" class="text-[10px] px-1">{{ bulkByType.suite.length }}</Badge>
                  </TabsTrigger>
                  <TabsTrigger value="accessible" class="flex-1 text-xs gap-1">
                    Nogironlar
                    <Badge variant="secondary" class="text-[10px] px-1">{{ bulkByType.accessible.length }}</Badge>
                  </TabsTrigger>
                </TabsList>
              </Tabs>

              <!-- Rooms grid -->
              <div class="max-h-72 overflow-y-auto border rounded-lg p-3">
                <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
                  <div
                    v-for="(room, idx) in bulkRooms"
                    :key="room.room_number"
                    :class="cn(
                      'border rounded-lg p-2.5 transition-all',
                      room.exists
                        ? 'bg-muted/60 opacity-40'
                        : room.room_type === 'single' ? 'border-blue-300 bg-blue-50/50'
                        : room.room_type === 'double' ? 'border-green-300 bg-green-50/50'
                        : room.room_type === 'suite' ? 'border-purple-300 bg-purple-50/50'
                        : room.room_type === 'accessible' ? 'border-amber-300 bg-amber-50/50'
                        : 'border-dashed'
                    )"
                  >
                    <template v-if="room.exists">
                      <div class="flex items-center justify-between">
                        <span class="text-sm font-bold">#{{ room.room_number }}</span>
                        <span class="text-[10px] text-muted-foreground">Mavjud</span>
                      </div>
                    </template>
                    <template v-else>
                      <!-- Row 1: number + proximity (clickable text) -->
                      <div class="flex items-center justify-between mb-1.5">
                        <span class="text-sm font-bold">#{{ room.room_number }}</span>
                        <button
                          type="button"
                          class="text-[10px] font-medium text-primary hover:underline cursor-pointer"
                          @click="toggleBulkProximity(idx)"
                        >{{ PROX_SHORT[room.proximity] }}</button>
                      </div>
                      <!-- Row 2: price input -->
                      <input
                        v-model.number="room.price_som"
                        type="number"
                        min="1"
                        class="w-full text-xs border rounded px-2 py-1 mb-1.5 bg-background focus:outline-none focus:ring-1 focus:ring-ring tabular-nums"
                      />
                      <!-- Row 3: select button -->
                      <button
                        type="button"
                        :class="cn(
                          'w-full text-[10px] font-medium py-1 rounded border transition-colors cursor-pointer',
                          room.room_type
                            ? room.room_type === bulkActiveType
                              ? 'bg-primary text-primary-foreground border-primary'
                              : room.room_type === 'single' ? 'bg-blue-100 text-blue-700 border-blue-300'
                              : room.room_type === 'double' ? 'bg-green-100 text-green-700 border-green-300'
                              : room.room_type === 'suite' ? 'bg-purple-100 text-purple-700 border-purple-300'
                              : 'bg-amber-100 text-amber-700 border-amber-300'
                            : 'bg-background hover:bg-muted border-border'
                        )"
                        @click="assignBulkType(idx)"
                      >
                        {{ room.room_type ? TYPE_UZ[room.room_type] : 'Tanlash' }}
                      </button>
                    </template>
                  </div>
                </div>
              </div>

              <!-- Status -->
              <div class="flex items-center justify-between text-xs">
                <span v-if="bulkUnassigned.length" class="text-amber-600 font-medium">
                  {{ bulkUnassigned.length }} ta belgilanmagan
                </span>
                <span v-else class="text-green-600 font-medium">Hammasi tayyor</span>
                <span class="text-muted-foreground">Qo'shiladi: {{ bulkReady.length }}</span>
              </div>

              <DialogFooter>
                <Button variant="outline" @click="editorOpen = false; bulkStep = 'setup'; bulkRooms = []" :disabled="bulkSaving">Bekor</Button>
                <Button :disabled="bulkSaving || !bulkReady.length" @click="saveBulk">
                  <Loader2 v-if="bulkSaving" class="w-4 h-4 mr-2 animate-spin" />
                  {{ bulkReady.length }} ta qo'shish
                </Button>
              </DialogFooter>
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>

    <!-- Delete Dialog -->
    <Dialog :open="deleteDialogOpen" @update:open="deleteDialogOpen = $event">
      <DialogContent class="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>{{ deleteConfirmed ? 'Tasdiqlaysizmi?' : `#${toDelete?.room_number}-xona o'chirilsinmi?` }}</DialogTitle>
          <p class="text-sm text-muted-foreground">{{ deleteWarning || "Bu amalni bekor qilib bo'lmaydi." }}</p>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" @click="deleteDialogOpen = false; deleteConfirmed = false; deleteWarning = ''">Bekor qilish</Button>
          <Button variant="destructive" @click="confirmDelete">
            {{ deleteConfirmed ? "Ha, o'chirish" : "O'chirish" }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Check-in Dialog -->
    <Dialog :open="checkInOpen" @update:open="(v: boolean) => { if (!v) { checkInOpen = false; checkInRoom = null } }">
      <DialogContent class="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>
            {{ checkInRoom ? `#${checkInRoom.room_number}-xonaga mehmon qabul qilish` : 'Mehmonni qabul qilish' }}
          </DialogTitle>
        </DialogHeader>
        <CheckInForm
          :room="checkInRoom"
          @cancel="checkInOpen = false; checkInRoom = null"
          @success="onCheckInSuccess"
        />
      </DialogContent>
    </Dialog>

    <!-- Room Detail Dialog -->
    <RoomDetail :room="detailRoom" :open="detailRoom !== null" @close="detailRoom = null" />
  </div>
</template>
