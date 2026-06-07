<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { housekeepingApi, type CleaningEntry } from '@/api/housekeeping'
import { receptionApi, type Room } from '@/api/reception'
import { useHousekeepingStore } from '@/stores/housekeeping'
import { useWsStore } from '@/stores/ws'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { parseApiError } from '@/composables/useOptimistic'
import { cn } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'
import { Play, CheckCircle, Camera, AlertTriangle, Loader2, Image, Clock, Sparkles, Plus } from 'lucide-vue-next'

const store = useHousekeepingStore()
const ws = useWsStore()
const auth = useAuthStore()
const toast = useToastStore()

const photoRequired = ref(true)

const completing = ref<CleaningEntry | null>(null)
const photoFile = ref<File | null>(null)
const photoPreview = ref<string | null>(null)
const submitting = ref(false)
const viewingPhoto = ref<string | null>(null)

onMounted(async () => {
  store.load()
  loadHistory()
  try {
    const s = await housekeepingApi.getSettings()
    photoRequired.value = s.photo_required
  } catch { /* default true */ }
})

const history = ref<CleaningEntry[]>([])
async function loadHistory() {
  try { history.value = await housekeepingApi.listHistory() }
  catch { /* ignore */ }
}

watch(
  () => ws.lastEvent,
  (env) => {
    const ch = env?.channel
    if (!ch) return
    if (ch.startsWith('rooms.') || ch.startsWith('housekeeping.')) { store.load(); loadHistory() }
    if (ch === 'housekeeping.settings_changed') {
      const pr = env.payload?.photo_required
      if (typeof pr === 'boolean') photoRequired.value = pr
    }
  }
)

const prefLabels: Record<string, string> = {
  morning: 'Ertalab',
  afternoon: 'Tushdan keyin',
  evening: 'Kechqurun',
  custom: 'Maxsus vaqt'
}

const now = ref(Date.now())
let tickHandle: number | undefined
onMounted(() => { tickHandle = window.setInterval(() => (now.value = Date.now()), 1000) })
onUnmounted(() => { if (tickHandle !== undefined) window.clearInterval(tickHandle) })

function elapsedSince(iso: string | null): string {
  if (!iso) return '—'
  const ms = Math.max(0, now.value - new Date(iso).getTime())
  const totalSeconds = Math.floor(ms / 1000)
  const m = Math.floor(totalSeconds / 60)
  const s = totalSeconds % 60
  return m > 0 ? `${m} daq ${s.toString().padStart(2, '0')} son` : `${s} son`
}

const canWork = computed(() => auth.role === 'manager' || auth.role === 'cleaner')
const isManager = computed(() => auth.role === 'manager')

async function startEntry(entry: CleaningEntry) {
  try {
    const updated = await housekeepingApi.start(entry.id)
    store.upsert(updated)
    toast.info(`#${updated.room_number}-xona tozalashi boshlandi`)
  } catch (e) { toast.error(`Xato: ${parseApiError(e)}`) }
}

function openComplete(entry: CleaningEntry) {
  completing.value = entry
  photoFile.value = null
  photoPreview.value = null
}

function onPhotoSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  photoFile.value = file
  photoPreview.value = URL.createObjectURL(file)
}

const canSubmitComplete = computed(() => {
  if (photoRequired.value) return photoFile.value !== null
  return true
})

async function submitComplete() {
  if (!completing.value) return
  submitting.value = true
  try {
    const updated = await housekeepingApi.complete(completing.value.id, photoFile.value)
    store.upsert(updated)
    toast.info(`#${updated.room_number}-xona toza deb belgilandi`)
    completing.value = null
    loadHistory()
  } catch (e) { toast.error(`Xato: ${parseApiError(e)}`) }
  finally { submitting.value = false }
}

async function togglePhotoRequired() {
  const next = !photoRequired.value
  try {
    const s = await housekeepingApi.updateSettings(next)
    photoRequired.value = s.photo_required
    toast.info(next ? 'Rasm endi majburiy' : 'Rasm endi ixtiyoriy')
  } catch (e) { toast.error(`Xato: ${parseApiError(e)}`) }
}

async function viewPhoto(path: string) {
  try { viewingPhoto.value = await housekeepingApi.fetchPhoto(path) }
  catch { toast.error("Rasmni yuklab bo'lmadi") }
}

// Stats — match maintenance layout (4 cards)
const dndPending = computed(() => store.pending.filter((e) => e.do_not_disturb).length)
const completedToday = computed(() => {
  const today = new Date().toDateString()
  return history.value.filter((e) => e.completed_at && new Date(e.completed_at).toDateString() === today).length
})

// Manual enqueue (manager only)
const newOpen = ref(false)
const rooms = ref<Room[]>([])
const roomsLoading = ref(false)
const newRoomId = ref<string>('')
const newPref = ref<'morning' | 'afternoon' | 'evening' | 'custom'>('afternoon')
const newPrefNote = ref('')
const creating = ref(false)

async function openNewDialog() {
  newOpen.value = true
  newRoomId.value = ''
  newPref.value = 'afternoon'
  newPrefNote.value = ''
  if (!rooms.value.length) {
    roomsLoading.value = true
    try {
      const res = await receptionApi.listRooms()
      rooms.value = res.rooms
    } catch { /* ignore */ }
    finally { roomsLoading.value = false }
  }
}

const availableRooms = computed(() => {
  const queued = new Set([...store.pending, ...store.inProgress].map((e) => e.room_id))
  return rooms.value.filter((r) => !queued.has(r.id))
})

async function submitNew() {
  const room = rooms.value.find((r) => r.id === newRoomId.value)
  if (!room) return
  creating.value = true
  try {
    const created = await housekeepingApi.enqueue({
      room_id: room.id,
      room_number: room.room_number,
      floor: room.floor,
      cleaning_preference: newPref.value,
      cleaning_preference_note: newPref.value === 'custom' ? (newPrefNote.value || null) : null,
    })
    store.upsert(created)
    toast.info(`#${created.room_number}-xona navbatga qo'shildi`)
    newOpen.value = false
  } catch (e) { toast.error(`Xato: ${parseApiError(e)}`) }
  finally { creating.value = false }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Stats — mirrors maintenance layout -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <Card>
        <CardContent class="p-4 text-center">
          <p class="text-2xl font-bold text-destructive">{{ dndPending }}</p>
          <p class="text-xs text-muted-foreground">Bezovta etmang</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent class="p-4 text-center">
          <p class="text-2xl font-bold text-amber-600">{{ store.pending.length }}</p>
          <p class="text-xs text-muted-foreground">Kutmoqda</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent class="p-4 text-center">
          <p class="text-2xl font-bold text-primary">{{ store.inProgress.length }}</p>
          <p class="text-xs text-muted-foreground">Bajarilmoqda</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent class="p-4 text-center">
          <p class="text-2xl font-bold text-green-600">{{ completedToday }}</p>
          <p class="text-xs text-muted-foreground">Bugun tugatildi</p>
        </CardContent>
      </Card>
    </div>

    <Tabs default-value="open">
      <div class="flex items-center justify-between">
        <TabsList>
          <TabsTrigger value="open">Ochiq ({{ store.pending.length + store.inProgress.length }})</TabsTrigger>
          <TabsTrigger value="history">Tarix ({{ history.length }})</TabsTrigger>
        </TabsList>
        <div class="flex items-center gap-3">
          <div v-if="isManager" class="flex items-center gap-2">
            <span class="text-sm text-muted-foreground">Rasm majburiy</span>
            <button
              type="button"
              :class="cn('relative inline-flex h-6 w-11 items-center rounded-full transition-colors cursor-pointer', photoRequired ? 'bg-primary' : 'bg-muted')"
              :aria-pressed="photoRequired"
              @click="togglePhotoRequired"
            >
              <span :class="cn('inline-block h-4 w-4 transform rounded-full bg-white transition-transform', photoRequired ? 'translate-x-6' : 'translate-x-1')" />
            </button>
          </div>
          <Button v-if="isManager" size="sm" @click="openNewDialog">
            <Plus class="w-4 h-4 mr-1" />
            Yangi tozalash
          </Button>
        </div>
      </div>

      <!-- OPEN (Kanban) -->
      <TabsContent value="open" class="space-y-4">
        <div v-if="store.error" class="rounded-md bg-destructive/10 text-destructive text-sm p-4">{{ store.error }}</div>
        <div v-if="store.loading && !store.entries.length" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Card v-for="i in 2" :key="i">
            <CardContent class="p-4 space-y-3">
              <Skeleton class="h-5 w-28" />
              <Skeleton class="h-20 w-full" />
            </CardContent>
          </Card>
        </div>
        <div v-else-if="!store.pending.length && !store.inProgress.length" class="text-center py-8 text-muted-foreground">Ochiq tozalash yo'q.</div>

        <!-- Kanban Board -->
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <!-- Kutmoqda (pending) -->
          <div class="space-y-3">
            <div class="flex items-center gap-2 pb-2 border-b border-amber-200 dark:border-amber-900">
              <Clock class="w-4 h-4 text-amber-600" />
              <span class="text-sm font-semibold">Kutmoqda</span>
              <Badge variant="warning" class="text-[10px] ml-auto">{{ store.pending.length }}</Badge>
            </div>
            <Card
              v-for="e in store.pending"
              :key="e.id"
              class="border-l-3 border-l-amber-400"
            >
              <CardContent class="p-3 space-y-2">
                <div class="flex items-center justify-between">
                  <span class="font-mono font-bold text-sm">#{{ e.room_number }}-xona</span>
                  <span class="text-[10px] text-muted-foreground">{{ e.floor }}-qavat · {{ new Date(e.queued_at).toLocaleTimeString('uz-UZ') }}</span>
                </div>
                <div v-if="e.do_not_disturb" class="flex items-center gap-1.5 text-[11px] font-medium text-amber-600 bg-warning/10 rounded px-1.5 py-1">
                  <AlertTriangle class="w-3 h-3" />
                  Bezovta qilmang
                </div>
                <p class="text-[11px] text-muted-foreground">
                  Afzal: {{ prefLabels[e.cleaning_preference] || e.cleaning_preference }}<span v-if="e.cleaning_preference_note"> — "{{ e.cleaning_preference_note }}"</span>
                </p>
                <Button v-if="canWork" size="xs" class="w-full" :disabled="e.do_not_disturb" @click="startEntry(e)">
                  <Play class="w-3 h-3 mr-1" />
                  Boshlash
                </Button>
              </CardContent>
            </Card>
            <p v-if="!store.pending.length" class="text-xs text-muted-foreground text-center py-4">—</p>
          </div>

          <!-- Bajarilmoqda (in_progress) -->
          <div class="space-y-3">
            <div class="flex items-center gap-2 pb-2 border-b border-blue-200 dark:border-blue-900">
              <Sparkles class="w-4 h-4 text-blue-600" />
              <span class="text-sm font-semibold">Bajarilmoqda</span>
              <Badge variant="default" class="text-[10px] ml-auto">{{ store.inProgress.length }}</Badge>
            </div>
            <Card
              v-for="e in store.inProgress"
              :key="e.id"
              class="border-l-3 border-l-blue-500"
            >
              <CardContent class="p-3 space-y-2">
                <div class="flex items-center justify-between">
                  <span class="font-mono font-bold text-sm">#{{ e.room_number }}-xona</span>
                  <span class="text-[10px] text-muted-foreground">{{ e.floor }}-qavat</span>
                </div>
                <div class="bg-primary/5 text-primary font-mono font-semibold text-center py-1.5 rounded text-xs tabular-nums">
                  {{ elapsedSince(e.started_at) }}
                </div>
                <Button v-if="canWork" size="xs" variant="success" class="w-full" @click="openComplete(e)">
                  <CheckCircle class="w-3 h-3 mr-1" />
                  Toza deb belgilash
                </Button>
              </CardContent>
            </Card>
            <p v-if="!store.inProgress.length" class="text-xs text-muted-foreground text-center py-4">—</p>
          </div>
        </div>
      </TabsContent>

      <!-- History -->
      <TabsContent value="history">
        <div v-if="!history.length" class="text-center py-8 text-muted-foreground">Tugatilgan tozalashlar yo'q.</div>
        <Card v-else>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Xona</TableHead>
                <TableHead>Qavat</TableHead>
                <TableHead>Tugatildi</TableHead>
                <TableHead>Rasm</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="e in history" :key="e.id">
                <TableCell class="font-mono">#{{ e.room_number }}</TableCell>
                <TableCell>{{ e.floor }}-qavat</TableCell>
                <TableCell class="text-muted-foreground">{{ e.completed_at ? new Date(e.completed_at).toLocaleString('uz-UZ') : '—' }}</TableCell>
                <TableCell>
                  <Button v-if="e.photo_path" variant="ghost" size="xs" @click="viewPhoto(e.photo_path)">
                    <Image class="w-3.5 h-3.5 mr-1" />
                    Ko'rish
                  </Button>
                  <span v-else class="text-muted-foreground">—</span>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </Card>
      </TabsContent>
    </Tabs>

    <!-- Complete dialog with photo -->
    <Dialog :open="completing !== null" @update:open="completing = null">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{{ completing ? `#${completing.room_number}-xona tozalandi` : '' }}</DialogTitle>
        </DialogHeader>
        <div class="space-y-4">
          <p class="text-sm text-muted-foreground">
            {{ photoRequired ? 'Tozalanganini tasdiqlash uchun rasm oling.' : 'Rasm olishingiz mumkin (ixtiyoriy).' }}
          </p>
          <label class="block cursor-pointer">
            <input type="file" accept="image/*" capture="environment" class="hidden" @change="onPhotoSelected" />
            <div v-if="!photoPreview" class="border-2 border-dashed rounded-lg p-8 text-center text-muted-foreground hover:border-primary hover:text-primary transition-colors">
              <Camera class="w-8 h-8 mx-auto mb-2" />
              <span class="text-sm">Rasmga olish / tanlash</span>
            </div>
            <img v-else :src="photoPreview" class="w-full max-h-64 object-contain rounded-lg" alt="tozalangan xona" />
          </label>
          <p v-if="photoRequired && !photoFile" class="text-xs text-amber-600">Rasm yuklash majburiy</p>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="completing = null">Bekor</Button>
          <Button variant="success" :disabled="!canSubmitComplete || submitting" @click="submitComplete">
            <Loader2 v-if="submitting" class="w-4 h-4 mr-2 animate-spin" />
            Tozalandi
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- New cleaning entry dialog -->
    <Dialog :open="newOpen" @update:open="newOpen = $event">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Yangi tozalash navbati</DialogTitle>
        </DialogHeader>
        <div class="space-y-4">
          <div class="space-y-2">
            <Label>Xona</Label>
            <Select v-model="newRoomId">
              <SelectTrigger><SelectValue placeholder="Xonani tanlang" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-if="roomsLoading" disabled value="__loading">Yuklanmoqda...</SelectItem>
                <SelectItem v-else-if="!availableRooms.length" disabled value="__empty">Bo'sh xonalar yo'q</SelectItem>
                <SelectItem v-for="r in availableRooms" :key="r.id" :value="r.id">
                  #{{ r.room_number }}-xona — {{ r.floor }}-qavat
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="space-y-2">
            <Label>Tozalash vaqti</Label>
            <Select v-model="newPref">
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="morning">Ertalab</SelectItem>
                <SelectItem value="afternoon">Tushdan keyin</SelectItem>
                <SelectItem value="evening">Kechqurun</SelectItem>
                <SelectItem value="custom">Maxsus vaqt</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div v-if="newPref === 'custom'" class="space-y-2">
            <Label>Izoh</Label>
            <Input v-model="newPrefNote" placeholder="Masalan: 14:30 dan keyin" maxlength="200" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" :disabled="creating" @click="newOpen = false">Bekor</Button>
          <Button :disabled="!newRoomId || newRoomId.startsWith('__') || creating" @click="submitNew">
            <Loader2 v-if="creating" class="w-4 h-4 mr-2 animate-spin" />
            Navbatga qo'shish
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Photo viewer -->
    <Dialog :open="viewingPhoto !== null" @update:open="viewingPhoto = null">
      <DialogContent class="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Tozalash isboti</DialogTitle>
        </DialogHeader>
        <img v-if="viewingPhoto" :src="viewingPhoto" class="w-full rounded-lg" alt="tozalash isboti" />
      </DialogContent>
    </Dialog>
  </div>
</template>
