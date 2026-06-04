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
import { useMaintenanceStore } from '@/stores/maintenance'
import { useWsStore } from '@/stores/ws'
import { useAuthStore } from '@/stores/auth'
import { parseApiError, useOptimistic } from '@/composables/useOptimistic'
import { URGENCY_UZ } from '@/lib/labels'
import { cn } from '@/lib/utils'
import { AlertTriangle, Plus, CheckCircle, UserPlus } from 'lucide-vue-next'

const store = useMaintenanceStore()
const ws = useWsStore()
const auth = useAuthStore()

const reportOpen = ref(false)
const resolved = ref<Issue[]>([])
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
  store.load()
  if (isManager.value) loadHistory()
})

watch(
  () => ws.lastEvent,
  (env) => {
    if (env?.channel?.startsWith('maintenance.')) {
      store.load()
      if (isManager.value) loadHistory()
    }
  }
)

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
    ok: (u) => { store.removeById(u.id); if (isManager.value) loadHistory() },
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
    <!-- ===== TECHNICIAN LAYOUT ===== -->
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

      <!-- My queue -->
      <div class="space-y-3">
        <h3 class="text-sm font-semibold">Mening navbatim ({{ mine.length }})</h3>
        <div v-if="!mine.length" class="text-center py-8 text-muted-foreground text-sm">Sizga tayinlangan muammo yo'q.</div>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Card v-for="i in mine" :key="i.id" class="border-l-4" :class="i.urgency === 'critical' ? 'border-l-destructive' : i.urgency === 'high' ? 'border-l-amber-400' : 'border-l-primary'">
            <CardContent class="p-4 space-y-2">
              <div class="flex items-center justify-between">
                <span class="font-mono font-semibold">#{{ i.room_number }} <span class="text-muted-foreground font-normal">/ {{ i.floor }}q</span></span>
                <Badge :variant="urgencyVariant(i.urgency)">{{ URGENCY_UZ[i.urgency] || i.urgency }}</Badge>
              </div>
              <p class="text-sm">{{ i.description }}</p>
              <Button size="sm" variant="success" class="w-full" @click="resolve(i)">
                <CheckCircle class="w-4 h-4 mr-1" />
                Hal qilindi
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      <!-- Available to claim -->
      <div class="space-y-3">
        <h3 class="text-sm font-semibold">Ochiq muammolar ({{ unassigned.length }})</h3>
        <div v-if="!unassigned.length" class="text-center py-6 text-muted-foreground text-sm">Ochiq muammolar yo'q.</div>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Card v-for="i in unassigned" :key="i.id">
            <CardContent class="p-4 space-y-2">
              <div class="flex items-center justify-between">
                <span class="font-mono font-semibold">#{{ i.room_number }} <span class="text-muted-foreground font-normal">/ {{ i.floor }}q</span></span>
                <Badge :variant="urgencyVariant(i.urgency)">{{ URGENCY_UZ[i.urgency] || i.urgency }}</Badge>
              </div>
              <p class="text-sm">{{ i.description }}</p>
              <p class="text-xs text-muted-foreground">{{ new Date(i.reported_at).toLocaleString('uz-UZ') }}</p>
              <Button size="sm" class="w-full" @click="claim(i)">
                <UserPlus class="w-4 h-4 mr-1" />
                Qabul qilish
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </template>

    <!-- ===== MANAGER / RECEPTION LAYOUT ===== -->
    <template v-else>
      <!-- Action bar -->
      <div class="flex justify-end">
        <Button v-if="canReport" size="sm" @click="reportOpen = true">
          <Plus class="w-4 h-4 mr-1" />
          Muammo qayd etish
        </Button>
      </div>

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

      <!-- Tabs: Ochiq / Jarayonda / Tarix -->
      <Tabs v-else default-value="open">
        <TabsList>
          <TabsTrigger value="open">Tayinlanmagan ({{ unassigned.length }})</TabsTrigger>
          <TabsTrigger value="assigned">Jarayonda ({{ assigned.length }})</TabsTrigger>
          <TabsTrigger value="resolved">Hal qilingan ({{ resolved.length }})</TabsTrigger>
        </TabsList>

        <!-- Open/Unassigned -->
        <TabsContent value="open">
          <div v-if="!unassigned.length" class="text-center py-8 text-muted-foreground text-sm">Ochiq muammolar yo'q.</div>
          <Card v-else>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Xona</TableHead>
                  <TableHead>Daraja</TableHead>
                  <TableHead>Tavsif</TableHead>
                  <TableHead>Qayd etildi</TableHead>
                  <TableHead class="text-right">Harakat</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="i in unassigned" :key="i.id">
                  <TableCell class="font-mono">#{{ i.room_number }} <span class="text-muted-foreground">/ {{ i.floor }}q</span></TableCell>
                  <TableCell><Badge :variant="urgencyVariant(i.urgency)">{{ URGENCY_UZ[i.urgency] || i.urgency }}</Badge></TableCell>
                  <TableCell class="max-w-[300px]">{{ i.description }}</TableCell>
                  <TableCell class="text-muted-foreground text-xs">{{ new Date(i.reported_at).toLocaleString('uz-UZ') }}</TableCell>
                  <TableCell class="text-right">
                    <Button size="xs" @click="claim(i)">
                      <UserPlus class="w-3 h-3 mr-1" />
                      Tayinlash
                    </Button>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        <!-- Assigned / In progress -->
        <TabsContent value="assigned">
          <div v-if="!assigned.length" class="text-center py-8 text-muted-foreground text-sm">Jarayondagi muammolar yo'q.</div>
          <Card v-else>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Xona</TableHead>
                  <TableHead>Daraja</TableHead>
                  <TableHead>Tavsif</TableHead>
                  <TableHead>Tayinlandi</TableHead>
                  <TableHead class="text-right">Harakat</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="i in assigned" :key="i.id">
                  <TableCell class="font-mono">#{{ i.room_number }} <span class="text-muted-foreground">/ {{ i.floor }}q</span></TableCell>
                  <TableCell><Badge :variant="urgencyVariant(i.urgency)">{{ URGENCY_UZ[i.urgency] || i.urgency }}</Badge></TableCell>
                  <TableCell class="max-w-[300px]">{{ i.description }}</TableCell>
                  <TableCell class="text-muted-foreground text-xs">{{ i.assigned_at ? new Date(i.assigned_at).toLocaleString('uz-UZ') : '—' }}</TableCell>
                  <TableCell class="text-right">
                    <Button size="xs" variant="success" @click="resolve(i)">
                      <CheckCircle class="w-3 h-3 mr-1" />
                      Hal qilindi
                    </Button>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Card>
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
  </div>
</template>
