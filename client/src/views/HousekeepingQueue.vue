<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { housekeepingApi, type CleaningEntry } from '@/api/housekeeping'
import { useHousekeepingStore } from '@/stores/housekeeping'
import { useWsStore } from '@/stores/ws'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { parseApiError } from '@/composables/useOptimistic'
import { cn } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'
import { Play, CheckCircle, Camera, AlertTriangle, Loader2, Image } from 'lucide-vue-next'

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
</script>

<template>
  <div class="space-y-6">
    <Tabs default-value="pending">
      <div class="flex items-center justify-between">
        <TabsList>
          <TabsTrigger value="pending">Kutmoqda ({{ store.pending.length }})</TabsTrigger>
          <TabsTrigger value="in_progress">Bajarilmoqda ({{ store.inProgress.length }})</TabsTrigger>
          <TabsTrigger value="history">Tarix ({{ history.length }})</TabsTrigger>
        </TabsList>
        <div v-if="isManager" class="flex items-center gap-3">
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
      </div>

      <!-- Pending -->
      <TabsContent value="pending" class="space-y-4">
        <div v-if="store.error" class="rounded-md bg-destructive/10 text-destructive text-sm p-4">{{ store.error }}</div>
        <div v-if="store.loading && !store.entries.length" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card v-for="i in 3" :key="i">
            <CardContent class="p-4 space-y-3">
              <div class="flex items-center justify-between">
                <Skeleton class="h-5 w-28" />
                <Skeleton class="h-5 w-16 rounded-full" />
              </div>
              <Skeleton class="h-4 w-full" />
              <Skeleton class="h-4 w-3/4" />
              <Skeleton class="h-9 w-full rounded-md" />
            </CardContent>
          </Card>
        </div>
        <div v-else-if="!store.pending.length" class="text-center py-8 text-muted-foreground">Kutayotgan xonalar yo'q.</div>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card v-for="e in store.pending" :key="e.id" class="transition-all hover:shadow-md">
            <CardContent class="p-4 space-y-3">
              <div class="flex items-center justify-between">
                <span class="font-semibold">#{{ e.room_number }}-xona</span>
                <Badge variant="warning">Kutmoqda</Badge>
              </div>
              <div class="flex justify-between text-sm text-muted-foreground">
                <span>{{ e.floor }}-qavat</span>
                <span>{{ new Date(e.queued_at).toLocaleTimeString('uz-UZ') }}</span>
              </div>
              <div v-if="e.do_not_disturb" class="flex items-center gap-2 text-xs font-medium text-amber-600 bg-warning/10 rounded-md px-2 py-1.5">
                <AlertTriangle class="w-3.5 h-3.5" />
                Bezovta qilmang
              </div>
              <p class="text-xs text-muted-foreground">
                Afzal: {{ prefLabels[e.cleaning_preference] || e.cleaning_preference }}
                <span v-if="e.cleaning_preference_note"> — "{{ e.cleaning_preference_note }}"</span>
              </p>
              <Button v-if="canWork" size="sm" class="w-full" :disabled="e.do_not_disturb" @click="startEntry(e)">
                <Play class="w-4 h-4 mr-1" />
                Boshlash
              </Button>
            </CardContent>
          </Card>
        </div>
      </TabsContent>

      <!-- In Progress -->
      <TabsContent value="in_progress" class="space-y-4">
        <div v-if="!store.inProgress.length" class="text-center py-8 text-muted-foreground">Hozircha bajarilayotgan tozalash yo'q.</div>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card v-for="e in store.inProgress" :key="e.id" class="border-primary/30 transition-all hover:shadow-md">
            <CardContent class="p-4 space-y-3">
              <div class="flex items-center justify-between">
                <span class="font-semibold">#{{ e.room_number }}-xona</span>
                <Badge>Bajarilmoqda</Badge>
              </div>
              <div class="flex justify-between text-sm text-muted-foreground">
                <span>{{ e.floor }}-qavat</span>
                <span>boshlandi {{ e.started_at ? new Date(e.started_at).toLocaleTimeString('uz-UZ') : '' }}</span>
              </div>
              <div class="bg-primary/5 text-primary font-mono font-semibold text-center py-2 rounded-md tabular-nums">
                {{ elapsedSince(e.started_at) }}
              </div>
              <Button v-if="canWork" size="sm" variant="success" class="w-full" @click="openComplete(e)">
                <CheckCircle class="w-4 h-4 mr-1" />
                Toza deb belgilash
              </Button>
            </CardContent>
          </Card>
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
