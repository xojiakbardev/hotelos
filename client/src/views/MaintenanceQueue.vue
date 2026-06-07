<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import MaintenanceReport from './MaintenanceReport.vue'
import { maintenanceApi, type Issue } from '@/api/maintenance'
import { authApi, type UserOut } from '@/api/auth'
import { useMaintenanceStore } from '@/stores/maintenance'
import { useWsStore } from '@/stores/ws'
import { useAuthStore } from '@/stores/auth'
import { parseApiError, useOptimistic } from '@/composables/useOptimistic'
import { useToastStore } from '@/stores/toast'
import { URGENCY_UZ } from '@/lib/labels'
import { cn } from '@/lib/utils'
import { AlertTriangle, Plus, CheckCircle, UserPlus, Loader2, Wrench, Phone } from 'lucide-vue-next'

const store = useMaintenanceStore()
const ws = useWsStore()
const auth = useAuthStore()
const toast = useToastStore()

const reportOpen = ref(false)
const activeTab = ref('open')
const resolved = ref<Issue[]>([])

// Assign modal
const assignOpen = ref(false)
const assignIssue = ref<Issue | null>(null)
const technicians = ref<UserOut[]>([])
const techLoading = ref(false)
const assigning = ref<string | null>(null)

function openAssignModal(issue: Issue) {
  assignIssue.value = issue
  assignOpen.value = true
  loadTechnicians()
}

async function loadTechnicians() {
  techLoading.value = true
  try {
    technicians.value = await authApi.listUsers('technician')
  } catch { technicians.value = [] }
  finally { techLoading.value = false }
}

async function assignTo(techId: string) {
  if (!assignIssue.value) return
  assigning.value = techId
  try {
    await maintenanceApi.assign(assignIssue.value.id, techId)
    toast.success(`Muammo texnikka tayinlandi`)
    assignOpen.value = false
    activeTab.value = 'open'
    store.load(auth.role || undefined)
  } catch (e: any) {
    toast.error(e?.response?.data?.message || 'Tayinlashda xatolik')
  } finally {
    assigning.value = null
  }
}
const resolvedLoading = ref(false)

const isManager = computed(() => auth.role === 'manager')
const isTechnician = computed(() => auth.role === 'technician')
const canReport = computed(() => auth.role === 'manager' || auth.role === 'reception')
const canWork = computed(() => auth.role === 'manager' || auth.role === 'technician')

const unassigned = computed(() => store.unassigned)
const assigned = computed(() => store.assigned)
const mine = computed(() => store.mine.filter((i) => i.status !== 'resolved'))

const criticalOpen = computed(() =>
  [...unassigned.value, ...store.mine].filter(
    (i) => i.urgency === 'critical' && i.status !== 'resolved'
  )
)

onMounted(() => {
  store.load(auth.role || undefined)
  if (isManager.value) { loadHistory(); loadTechnicians() }
  if (isTechnician.value) loadMyResolved()
})

const techById = computed(() => {
  const m = new Map<string, UserOut>()
  for (const t of technicians.value) m.set(t.id, t)
  return m
})

watch(
  () => ws.lastEvent,
  (env) => {
    if (env?.channel?.startsWith('maintenance.')) {
      store.load(auth.role || undefined)
      if (isManager.value) loadHistory()
      if (isTechnician.value) loadMyResolved()
    }
  }
)

const myResolved = ref<Issue[]>([])

async function loadMyResolved() {
  try {
    const all = await maintenanceApi.myQueue()
    myResolved.value = all.filter(i => i.status === 'resolved')
  } catch { /* ignore */ }
}

async function loadHistory() {
  resolvedLoading.value = true
  try { resolved.value = await maintenanceApi.history() }
  catch { /* ignore */ }
  finally { resolvedLoading.value = false }
}

function urgencyVariant(u: string): 'destructive' | 'warning' | 'default' | 'secondary' {
  if (u === 'critical') return 'destructive'
  if (u === 'high') return 'warning'
  if (u === 'normal') return 'default'
  return 'secondary'
}

async function claim(issue: Issue) {
  const before = { ...issue }
  const run = useOptimistic({
    apply: () => {
      issue.status = 'assigned'
      issue.assigned_technician_id = auth.user?.id ?? null
      issue.assigned_at = new Date().toISOString()
    },
    revert: () => Object.assign(issue, before),
    call: () => maintenanceApi.claim(issue.id),
    ok: (u) => store.upsert(u),
    successMsg: (u) => `#${u.room_number}-xona qabul qilindi`,
    errorMsg: (e) => `Xato: ${parseApiError(e)}`
  })
  await run()
}

async function resolve(issue: Issue) {
  const before = { ...issue }
  const run = useOptimistic({
    apply: () => { issue.status = 'resolved'; issue.resolved_at = new Date().toISOString() },
    revert: () => Object.assign(issue, before),
    call: () => maintenanceApi.resolve(issue.id),
    ok: (u) => { store.removeById(u.id); if (isManager.value) loadHistory(); if (isTechnician.value) loadMyResolved() },
    successMsg: (u) => `#${u.room_number}-xona muammosi hal qilindi`,
    errorMsg: (e) => `Xato: ${parseApiError(e)}`
  })
  await run()
}

function onReported() {
  reportOpen.value = false
  store.load()
}
</script>

<template>
  <div class="space-y-6">
    <!-- ===== TECHNICIAN LAYOUT (kanban) ===== -->
    <template v-if="isTechnician">
      <!-- Critical alert -->
      <div v-if="criticalOpen.length" class="rounded-lg border-l-4 border-l-destructive bg-destructive/10 p-4 flex items-start gap-3" role="alert">
        <AlertTriangle class="w-5 h-5 text-destructive shrink-0 mt-0.5" />
        <div>
          <p class="font-bold text-destructive">{{ criticalOpen.length }} ta KRITIK muammo</p>
          <div class="flex flex-wrap gap-2 mt-1">
            <Badge v-for="i in criticalOpen" :key="i.id" variant="destructive">#{{ i.room_number }}</Badge>
          </div>
        </div>
      </div>

      <!-- Stats -->
      <div class="grid grid-cols-3 gap-3">
        <Card>
          <CardContent class="p-4 text-center">
            <p class="text-2xl font-bold text-amber-600">{{ unassigned.length }}</p>
            <p class="text-xs text-muted-foreground">Ochiq</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4 text-center">
            <p class="text-2xl font-bold text-primary">{{ mine.length }}</p>
            <p class="text-xs text-muted-foreground">Mening navbatim</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4 text-center">
            <p class="text-2xl font-bold text-green-600">{{ myResolved.length }}</p>
            <p class="text-xs text-muted-foreground">Hal qildim</p>
          </CardContent>
        </Card>
      </div>

      <Tabs default-value="open">
        <TabsList>
          <TabsTrigger value="open">Ochiq ({{ unassigned.length + mine.length }})</TabsTrigger>
          <TabsTrigger value="resolved">Tarix ({{ myResolved.length }})</TabsTrigger>
        </TabsList>

        <!-- OPEN: 3-column kanban -->
        <TabsContent value="open" class="space-y-4">
          <div v-if="!unassigned.length && !mine.length" class="text-center py-8 text-muted-foreground text-sm">Ochiq muammolar yo'q.</div>
          <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <!-- Ochiq (qabul qilish) -->
            <div class="space-y-3">
              <div class="flex items-center gap-2 pb-2 border-b border-amber-200 dark:border-amber-900">
                <AlertTriangle class="w-4 h-4 text-amber-600" />
                <span class="text-sm font-semibold">Ochiq</span>
                <Badge variant="warning" class="text-[10px] ml-auto">{{ unassigned.length }}</Badge>
              </div>
              <Card v-for="i in unassigned" :key="i.id" class="border-l-3" :class="i.urgency === 'critical' ? 'border-l-destructive' : 'border-l-amber-400'">
                <CardContent class="p-3 space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="font-mono font-bold text-sm">#{{ i.room_number }} <span class="text-muted-foreground font-normal">/ {{ i.floor }}q</span></span>
                    <Badge :variant="urgencyVariant(i.urgency)" class="text-[10px]">{{ URGENCY_UZ[i.urgency] || i.urgency }}</Badge>
                  </div>
                  <p class="text-xs">{{ i.description }}</p>
                  <p class="text-[10px] text-muted-foreground">{{ new Date(i.reported_at).toLocaleString('uz-UZ') }}</p>
                  <Button size="xs" class="w-full" @click="claim(i)">
                    <UserPlus class="w-3 h-3 mr-1" />
                    Qabul qilish
                  </Button>
                </CardContent>
              </Card>
              <p v-if="!unassigned.length" class="text-xs text-muted-foreground text-center py-4">—</p>
            </div>

            <!-- Mening navbatim -->
            <div class="space-y-3">
              <div class="flex items-center gap-2 pb-2 border-b border-blue-200 dark:border-blue-900">
                <Wrench class="w-4 h-4 text-blue-600" />
                <span class="text-sm font-semibold">Mening navbatim</span>
                <Badge variant="default" class="text-[10px] ml-auto">{{ mine.length }}</Badge>
              </div>
              <Card v-for="i in mine" :key="i.id" class="border-l-3 border-l-blue-500">
                <CardContent class="p-3 space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="font-mono font-bold text-sm">#{{ i.room_number }} <span class="text-muted-foreground font-normal">/ {{ i.floor }}q</span></span>
                    <Badge :variant="urgencyVariant(i.urgency)" class="text-[10px]">{{ URGENCY_UZ[i.urgency] || i.urgency }}</Badge>
                  </div>
                  <p class="text-xs">{{ i.description }}</p>
                  <p class="text-[10px] text-muted-foreground">Tayinlandi: {{ i.assigned_at ? new Date(i.assigned_at).toLocaleString('uz-UZ') : '—' }}</p>
                  <Button size="xs" variant="success" class="w-full" @click="resolve(i)">
                    <CheckCircle class="w-3 h-3 mr-1" />
                    Hal qilindi
                  </Button>
                </CardContent>
              </Card>
              <p v-if="!mine.length" class="text-xs text-muted-foreground text-center py-4">—</p>
            </div>

            <!-- Hal qildim (recent) -->
            <div class="space-y-3">
              <div class="flex items-center gap-2 pb-2 border-b border-green-200 dark:border-green-900">
                <CheckCircle class="w-4 h-4 text-green-600" />
                <span class="text-sm font-semibold">Hal qildim</span>
                <Badge variant="success" class="text-[10px] ml-auto">{{ myResolved.slice(0, 5).length }}</Badge>
              </div>
              <Card v-for="i in myResolved.slice(0, 5)" :key="i.id" class="border-l-3 border-l-green-500 opacity-75">
                <CardContent class="p-3 space-y-1">
                  <div class="flex items-center justify-between">
                    <span class="font-mono font-bold text-sm">#{{ i.room_number }} <span class="text-muted-foreground font-normal">/ {{ i.floor }}q</span></span>
                    <span class="text-[10px] text-muted-foreground">{{ i.resolved_at ? new Date(i.resolved_at).toLocaleString('uz-UZ') : '' }}</span>
                  </div>
                  <p class="text-xs text-muted-foreground">{{ i.description }}</p>
                </CardContent>
              </Card>
              <p v-if="!myResolved.length" class="text-xs text-muted-foreground text-center py-4">—</p>
            </div>
          </div>
        </TabsContent>

        <!-- TARIX (full my-resolved history) -->
        <TabsContent value="resolved">
          <div v-if="!myResolved.length" class="text-center py-8 text-muted-foreground text-sm">Hal qilingan muammolar yo'q.</div>
          <Card v-else>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Xona</TableHead>
                  <TableHead>Daraja</TableHead>
                  <TableHead>Tavsif</TableHead>
                  <TableHead>Qayd etildi</TableHead>
                  <TableHead>Hal qildim</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="i in myResolved" :key="i.id">
                  <TableCell class="font-mono">#{{ i.room_number }} <span class="text-muted-foreground">/ {{ i.floor }}q</span></TableCell>
                  <TableCell><Badge :variant="urgencyVariant(i.urgency)">{{ URGENCY_UZ[i.urgency] || i.urgency }}</Badge></TableCell>
                  <TableCell class="max-w-[300px]">{{ i.description }}</TableCell>
                  <TableCell class="text-muted-foreground text-xs">{{ new Date(i.reported_at).toLocaleString('uz-UZ') }}</TableCell>
                  <TableCell class="text-muted-foreground text-xs">{{ i.resolved_at ? new Date(i.resolved_at).toLocaleString('uz-UZ') : '—' }}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Card>
        </TabsContent>
      </Tabs>
    </template>

    <!-- ===== MANAGER / RECEPTION LAYOUT ===== -->
    <template v-else>
      <!-- Critical alert -->
      <div v-if="criticalOpen.length" class="rounded-lg border-l-4 border-l-destructive bg-destructive/10 p-4 flex items-start gap-3 animate-pulse" role="alert">
        <AlertTriangle class="w-5 h-5 text-destructive shrink-0 mt-0.5" />
        <div>
          <p class="font-bold text-destructive">{{ criticalOpen.length }} ta KRITIK muammo darhol ko'rib chiqishni talab qiladi</p>
          <div class="flex flex-wrap gap-2 mt-2">
            <Badge v-for="i in criticalOpen" :key="i.id" variant="destructive">#{{ i.room_number }}-xona</Badge>
          </div>
        </div>
      </div>

      <!-- Stats -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card>
          <CardContent class="p-4 text-center">
            <p class="text-2xl font-bold text-destructive">{{ unassigned.filter(i => i.urgency === 'critical').length + unassigned.filter(i => i.urgency === 'high').length }}</p>
            <p class="text-xs text-muted-foreground">Shoshilinch</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4 text-center">
            <p class="text-2xl font-bold text-primary">{{ unassigned.length }}</p>
            <p class="text-xs text-muted-foreground">Tayinlanmagan</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4 text-center">
            <p class="text-2xl font-bold text-amber-600">{{ assigned.length }}</p>
            <p class="text-xs text-muted-foreground">Jarayonda</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4 text-center">
            <p class="text-2xl font-bold text-green-600">{{ resolved.length }}</p>
            <p class="text-xs text-muted-foreground">Hal qilingan</p>
          </CardContent>
        </Card>
      </div>

      <!-- States -->
      <div v-if="store.error" class="rounded-md bg-destructive/10 text-destructive text-sm p-4">{{ store.error }}</div>
      <div v-if="store.loading && !store.open.length" class="space-y-4">
        <Card v-for="i in 3" :key="i">
          <div class="p-4 flex items-center gap-4">
            <Skeleton class="h-4 w-16" />
            <Skeleton class="h-5 w-14 rounded-full" />
            <Skeleton class="h-4 w-48" />
            <Skeleton class="h-4 w-16 ml-auto" />
            <Skeleton class="h-8 w-24 rounded-md" />
          </div>
        </Card>
      </div>

      <!-- Tabs: Ochiq (kanban) / Tarix -->
      <Tabs v-else v-model="activeTab">
        <div class="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="open">Ochiq ({{ unassigned.length + assigned.length }})</TabsTrigger>
            <TabsTrigger value="resolved">Tarix ({{ resolved.length }})</TabsTrigger>
          </TabsList>
          <Button v-if="canReport" size="sm" @click="reportOpen = true">
            <Plus class="w-4 h-4 mr-1" />
            Muammo qayd etish
          </Button>
        </div>

        <!-- OPEN: 3-column kanban -->
        <TabsContent value="open" class="space-y-4">
          <div v-if="!unassigned.length && !assigned.length" class="text-center py-8 text-muted-foreground text-sm">Ochiq muammolar yo'q.</div>
          <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <!-- Tayinlanmagan -->
            <div class="space-y-3">
              <div class="flex items-center gap-2 pb-2 border-b border-amber-200 dark:border-amber-900">
                <AlertTriangle class="w-4 h-4 text-amber-600" />
                <span class="text-sm font-semibold">Tayinlanmagan</span>
                <Badge variant="warning" class="text-[10px] ml-auto">{{ unassigned.length }}</Badge>
              </div>
              <Card v-for="i in unassigned" :key="i.id" class="border-l-3" :class="i.urgency === 'critical' ? 'border-l-destructive' : 'border-l-amber-400'">
                <CardContent class="p-3 space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="font-mono font-bold text-sm">#{{ i.room_number }} <span class="text-muted-foreground font-normal">/ {{ i.floor }}q</span></span>
                    <Badge :variant="urgencyVariant(i.urgency)" class="text-[10px]">{{ URGENCY_UZ[i.urgency] || i.urgency }}</Badge>
                  </div>
                  <p class="text-xs">{{ i.description }}</p>
                  <p class="text-[10px] text-muted-foreground">{{ new Date(i.reported_at).toLocaleString('uz-UZ') }}</p>
                  <Button v-if="isManager" size="xs" class="w-full" @click="openAssignModal(i)">
                    <UserPlus class="w-3 h-3 mr-1" />
                    Tayinlash
                  </Button>
                  <Button v-else size="xs" class="w-full" @click="claim(i)">
                    <UserPlus class="w-3 h-3 mr-1" />
                    Qabul qilish
                  </Button>
                </CardContent>
              </Card>
              <p v-if="!unassigned.length" class="text-xs text-muted-foreground text-center py-4">—</p>
            </div>

            <!-- Tayinlangan -->
            <div class="space-y-3">
              <div class="flex items-center gap-2 pb-2 border-b border-blue-200 dark:border-blue-900">
                <Wrench class="w-4 h-4 text-blue-600" />
                <span class="text-sm font-semibold">Tayinlangan</span>
                <Badge variant="default" class="text-[10px] ml-auto">{{ assigned.length }}</Badge>
              </div>
              <Card v-for="i in assigned" :key="i.id" class="border-l-3 border-l-blue-500">
                <CardContent class="p-3 space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="font-mono font-bold text-sm">#{{ i.room_number }} <span class="text-muted-foreground font-normal">/ {{ i.floor }}q</span></span>
                    <Badge :variant="urgencyVariant(i.urgency)" class="text-[10px]">{{ URGENCY_UZ[i.urgency] || i.urgency }}</Badge>
                  </div>
                  <p class="text-xs">{{ i.description }}</p>
                  <div v-if="i.assigned_technician_name || i.assigned_technician_phone" class="bg-muted/40 rounded px-2 py-1.5 space-y-0.5">
                    <p class="text-[11px] font-medium">{{ i.assigned_technician_name || i.assigned_technician_phone }}</p>
                    <p v-if="i.assigned_technician_phone" class="text-[10px] text-muted-foreground flex items-center gap-1"><Phone class="w-2.5 h-2.5" /> {{ i.assigned_technician_phone }}</p>
                  </div>
                  <p class="text-[10px] text-muted-foreground">Tayinlandi: {{ i.assigned_at ? new Date(i.assigned_at).toLocaleString('uz-UZ') : '—' }}</p>
                  <Button size="xs" variant="success" class="w-full" @click="resolve(i)">
                    <CheckCircle class="w-3 h-3 mr-1" />
                    Hal qilindi
                  </Button>
                </CardContent>
              </Card>
              <p v-if="!assigned.length" class="text-xs text-muted-foreground text-center py-4">—</p>
            </div>

            <!-- Hal qilingan (recent, today) -->
            <div class="space-y-3">
              <div class="flex items-center gap-2 pb-2 border-b border-green-200 dark:border-green-900">
                <CheckCircle class="w-4 h-4 text-green-600" />
                <span class="text-sm font-semibold">Hal qilingan</span>
                <Badge variant="success" class="text-[10px] ml-auto">{{ resolved.slice(0, 5).length }}</Badge>
              </div>
              <Card v-for="i in resolved.slice(0, 5)" :key="i.id" class="border-l-3 border-l-green-500 opacity-75">
                <CardContent class="p-3 space-y-1">
                  <div class="flex items-center justify-between">
                    <span class="font-mono font-bold text-sm">#{{ i.room_number }} <span class="text-muted-foreground font-normal">/ {{ i.floor }}q</span></span>
                    <span class="text-[10px] text-muted-foreground">{{ i.resolved_at ? new Date(i.resolved_at).toLocaleString('uz-UZ') : '' }}</span>
                  </div>
                  <p class="text-xs text-muted-foreground">{{ i.description }}</p>
                </CardContent>
              </Card>
              <p v-if="!resolved.length" class="text-xs text-muted-foreground text-center py-4">—</p>
            </div>
          </div>
        </TabsContent>

        <!-- Resolved history -->
        <TabsContent value="resolved">
          <div v-if="resolvedLoading" class="text-center py-8 text-muted-foreground text-sm">Yuklanmoqda...</div>
          <div v-else-if="!resolved.length" class="text-center py-8 text-muted-foreground text-sm">Hal qilingan muammolar yo'q.</div>
          <Card v-else>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Xona</TableHead>
                  <TableHead>Daraja</TableHead>
                  <TableHead>Tavsif</TableHead>
                  <TableHead>Qayd etildi</TableHead>
                  <TableHead>Hal qilindi</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="i in resolved" :key="i.id">
                  <TableCell class="font-mono">#{{ i.room_number }} <span class="text-muted-foreground">/ {{ i.floor }}q</span></TableCell>
                  <TableCell><Badge :variant="urgencyVariant(i.urgency)">{{ URGENCY_UZ[i.urgency] || i.urgency }}</Badge></TableCell>
                  <TableCell class="max-w-[300px]">{{ i.description }}</TableCell>
                  <TableCell class="text-muted-foreground text-xs">{{ new Date(i.reported_at).toLocaleString('uz-UZ') }}</TableCell>
                  <TableCell class="text-muted-foreground text-xs">{{ i.resolved_at ? new Date(i.resolved_at).toLocaleString('uz-UZ') : '—' }}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Card>
        </TabsContent>
      </Tabs>
    </template>

    <!-- Report Dialog -->
    <Dialog :open="reportOpen" @update:open="reportOpen = $event">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Muammo qayd etish</DialogTitle>
        </DialogHeader>
        <MaintenanceReport @cancel="reportOpen = false" @success="onReported" />
      </DialogContent>
    </Dialog>

    <!-- Assign Dialog -->
    <Dialog :open="assignOpen" @update:open="assignOpen = $event">
      <DialogContent class="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Texnik tayinlash</DialogTitle>
        </DialogHeader>
        <div v-if="assignIssue" class="space-y-4">
          <div class="bg-muted/40 rounded-lg p-3 text-sm">
            <span class="font-mono font-bold">#{{ assignIssue.room_number }}</span>
            <span class="text-muted-foreground"> — {{ assignIssue.description.slice(0, 60) }}{{ assignIssue.description.length > 60 ? '...' : '' }}</span>
          </div>

          <div v-if="techLoading" class="space-y-2">
            <Skeleton class="h-10 w-full" />
            <Skeleton class="h-10 w-full" />
            <Skeleton class="h-10 w-full" />
          </div>
          <div v-else-if="!technicians.length" class="text-center py-4 text-muted-foreground text-sm">
            Texniklar topilmadi
          </div>
          <div v-else class="space-y-2">
            <button
              v-for="tech in technicians"
              :key="tech.id"
              class="w-full flex items-center justify-between p-3 rounded-lg border hover:bg-accent hover:border-primary/30 transition-all duration-150 cursor-pointer"
              :disabled="assigning !== null"
              @click="assignTo(tech.id)"
            >
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-full bg-primary/10 grid place-items-center text-xs font-bold text-primary">
                  {{ (tech.full_name || tech.phone).slice(0, 1).toUpperCase() }}
                </div>
                <div class="text-left">
                  <p class="text-sm font-medium">{{ tech.full_name || tech.phone }}</p>
                  <p class="text-xs text-muted-foreground">{{ tech.phone }}</p>
                </div>
              </div>
              <Loader2 v-if="assigning === tech.id" class="w-4 h-4 animate-spin text-primary" />
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  </div>
</template>
