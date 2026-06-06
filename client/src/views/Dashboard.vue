<script setup lang="ts">
import { computed, onMounted, watch, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useWsStore } from '@/stores/ws'
import { useRoomsStore } from '@/stores/rooms'
import { useHousekeepingStore } from '@/stores/housekeeping'
import { useOrdersStore } from '@/stores/orders'
import { useMaintenanceStore } from '@/stores/maintenance'
import { useGuestsStore } from '@/stores/guests'
import { metricsApi, type DashboardMetrics } from '@/api/metrics'
import { receptionApi, type DailyCount } from '@/api/reception'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { StatCard } from '@/components/ui/stat-card'
import {
  Users,
  Sparkles,
  UtensilsCrossed,
  Wrench,
  TrendingUp,
  Clock,
} from 'lucide-vue-next'

const auth = useAuthStore()
const ws = useWsStore()
const rooms = useRoomsStore()
const guests = useGuestsStore()
const housekeeping = useHousekeepingStore()
const orders = useOrdersStore()
const maintenance = useMaintenanceStore()

const metrics = ref<DashboardMetrics | null>(null)
const metricsLoading = ref(true)
const dailyStats = ref<DailyCount[]>([])
const chartPeriod = ref<'7' | '14' | '30'>('14')
const canSeeRevenue = computed(() => auth.role === 'manager')

async function loadMetrics() {
  if (!canSeeRevenue.value) { metricsLoading.value = false; return }
  try { metrics.value = await metricsApi.dashboard() } catch { /* tolerates stale */ }
  finally { metricsLoading.value = false }
}

async function loadDailyStats() {
  try { dailyStats.value = await receptionApi.dailyGuestStats(Number(chartPeriod.value)) } catch { /* ignore */ }
}

function money(minor: number) { return (minor / 100).toLocaleString('uz-UZ') + " so'm" }

onMounted(() => {
  rooms.load()
  loadMetrics()
  if (auth.role === 'manager' || auth.role === 'reception') {
    guests.load()
    orders.load()
    loadDailyStats()
  }
  if (auth.role === 'manager' || auth.role === 'cleaner') {
    housekeeping.load()
  }
  if (auth.role !== 'cleaner') {
    maintenance.load(auth.role || undefined)
  }
})

watch(
  () => ws.lastEvent,
  (env) => {
    const ch = env?.channel ?? ''
    const role = auth.role
    if (ch.startsWith('rooms.') || ch.startsWith('guests.')) rooms.load()
    if (ch.startsWith('guests.') && (role === 'manager' || role === 'reception')) { guests.load(); loadDailyStats() }
    if (ch.startsWith('rooms.') && (role === 'manager' || role === 'cleaner')) housekeeping.load()
    if (ch.startsWith('orders.') && (role === 'manager' || role === 'reception')) orders.load()
    if (ch.startsWith('maintenance.') && role !== 'cleaner') maintenance.load(role || undefined)
    if (
      (ch.startsWith('rooms.') || ch.startsWith('guests.') ||
       ch.startsWith('orders.') || ch.startsWith('bills.')) &&
      canSeeRevenue.value
    ) loadMetrics()
  }
)

const roomsOccupied = computed(() => rooms.rooms.filter((r) => r.status === 'occupied').length)
const roomsTotal = computed(() => rooms.rooms.length)
const cleaningOpen = computed(() => housekeeping.pending.length + housekeeping.inProgress.length)
const ordersOpen = computed(() => orders.open.length)
const openIssues = computed(() => maintenance.open.length)

// Chart computed
const chartMax = computed(() => Math.max(1, ...dailyStats.value.map(d => d.count)))
const chartBars = computed(() =>
  dailyStats.value.map(d => ({
    date: d.date,
    count: d.count,
    height: Math.max(4, Math.round((d.count / chartMax.value) * 160))
  }))
)

const avgCleaningTime = computed(() => {
  const entries = housekeeping.entries.filter(e => e.started_at && e.completed_at)
  if (!entries.length) return '—'
  const total = entries.reduce((sum, e) => {
    const ms = new Date(e.completed_at!).getTime() - new Date(e.started_at!).getTime()
    return sum + ms
  }, 0)
  const avgMin = Math.round(total / entries.length / 60000)
  return avgMin > 60 ? `${Math.floor(avgMin/60)} soat ${avgMin%60} daq` : `${avgMin} daq`
})

const avgOrderTime = computed(() => {
  const delivered = orders.orders.filter(o => o.delivered_at && o.received_at)
  if (!delivered.length) return '—'
  const total = delivered.reduce((sum, o) => {
    const ms = new Date(o.delivered_at!).getTime() - new Date(o.received_at).getTime()
    return sum + ms
  }, 0)
  const avgMin = Math.round(total / delivered.length / 60000)
  return avgMin > 60 ? `${Math.floor(avgMin/60)} soat ${avgMin%60} daq` : `${avgMin} daq`
})
</script>

<template>
  <div class="space-y-6">
    <!-- Top 4 stats -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <template v-if="metricsLoading || (rooms.loading && !rooms.rooms.length)">
        <Card v-for="i in 4" :key="i">
          <CardContent class="p-5">
            <div class="flex items-center justify-between">
              <div class="space-y-2">
                <Skeleton class="h-4 w-24" />
                <Skeleton class="h-7 w-16" />
                <Skeleton class="h-3 w-20" />
              </div>
              <Skeleton class="h-10 w-10 rounded-lg" />
            </div>
          </CardContent>
        </Card>
      </template>
      <template v-else>
        <!-- Faol mehmonlar -->
        <StatCard
          v-if="auth.role === 'manager' || auth.role === 'reception'"
          label="Faol mehmonlar"
          :value="guests.guests.length"
          :icon="Users"
          icon-color="primary"
          :animate="true"
        />

        <!-- Tozalash -->
        <StatCard
          v-if="auth.role === 'manager' || auth.role === 'cleaner'"
          label="Tozalash navbati"
          :value="cleaningOpen"
          :icon="Sparkles"
          icon-color="warning"
          :animate="true"
        />

        <!-- Buyurtmalar -->
        <StatCard
          v-if="auth.role === 'manager' || auth.role === 'reception'"
          label="Ochiq buyurtmalar"
          :value="ordersOpen"
          :icon="UtensilsCrossed"
          icon-color="primary"
          :animate="true"
        />

        <!-- Texnik -->
        <StatCard
          v-if="auth.role !== 'cleaner'"
          label="Texnik muammolar"
          :value="openIssues"
          :icon="Wrench"
          :icon-color="openIssues > 0 ? 'destructive' : 'success'"
          :animate="true"
        />
      </template>
    </div>

    <!-- Revenue row (manager only) -->
    <div v-if="canSeeRevenue && metrics" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <Card>
        <CardContent class="p-5">
          <div class="flex items-center justify-between">
            <div class="space-y-1">
              <p class="text-sm text-muted-foreground">Bugungi tushum</p>
              <p class="text-2xl font-bold tracking-tight">{{ money(metrics.revenue_today_minor_units) }}</p>
            </div>
            <div class="h-10 w-10 rounded-lg bg-success/10 grid place-items-center">
              <TrendingUp class="w-5 h-5 text-green-600" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent class="p-5">
          <div class="flex items-center justify-between">
            <div class="space-y-1">
              <p class="text-sm text-muted-foreground">7 kunlik tushum</p>
              <p class="text-2xl font-bold tracking-tight">{{ money(metrics.revenue_week_minor_units) }}</p>
            </div>
            <div class="h-10 w-10 rounded-lg bg-accent grid place-items-center">
              <TrendingUp class="w-5 h-5 text-muted-foreground" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Guest stats chart -->
    <Card v-if="(auth.role === 'manager' || auth.role === 'reception') && dailyStats.length">
      <CardHeader class="pb-2 flex flex-row items-center justify-between">
        <CardTitle class="text-sm font-semibold">Mehmonlar statistikasi</CardTitle>
        <div class="flex gap-1">
          <button
            v-for="p in [{v:'7',l:'1 hafta'},{v:'14',l:'2 hafta'},{v:'30',l:'1 oy'}]"
            :key="p.v"
            class="px-2.5 py-1 text-[11px] font-medium rounded-md transition-all duration-150 cursor-pointer"
            :class="chartPeriod === p.v ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'"
            @click="chartPeriod = p.v as '7'|'14'|'30'; loadDailyStats()"
          >
            {{ p.l }}
          </button>
        </div>
      </CardHeader>
      <CardContent>
        <div class="flex items-end gap-1" style="height: 200px;">
          <div
            v-for="bar in chartBars"
            :key="bar.date"
            class="flex-1 flex flex-col items-center justify-end h-full"
          >
            <span class="text-[9px] text-muted-foreground tabular-nums mb-1">{{ bar.count || '' }}</span>
            <div
              class="w-full rounded-t-sm bg-primary/80 transition-all duration-300 min-h-[2px]"
              :style="{ height: bar.height + 'px' }"
            />
            <span class="text-[8px] text-muted-foreground mt-1">{{ bar.date.slice(8) }}</span>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Performance grid -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card>
        <CardHeader class="pb-3">
          <CardTitle class="text-sm font-semibold flex items-center gap-2">
            <Sparkles class="w-4 h-4 text-muted-foreground" />
            Tozalash samaradorligi
          </CardTitle>
        </CardHeader>
        <CardContent class="space-y-3">
          <div class="flex justify-between items-center">
            <span class="text-sm text-muted-foreground">O'rtacha vaqt</span>
            <span class="text-sm font-semibold">{{ avgCleaningTime }}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-sm text-muted-foreground">Navbatda</span>
            <span class="text-sm font-semibold">{{ housekeeping.pending.length }}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-sm text-muted-foreground">Bajarilmoqda</span>
            <span class="text-sm font-semibold">{{ housekeeping.inProgress.length }}</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader class="pb-3">
          <CardTitle class="text-sm font-semibold flex items-center gap-2">
            <Clock class="w-4 h-4 text-muted-foreground" />
            Xona xizmati tezligi
          </CardTitle>
        </CardHeader>
        <CardContent class="space-y-3">
          <div class="flex justify-between items-center">
            <span class="text-sm text-muted-foreground">O'rtacha yetkazish</span>
            <span class="text-sm font-semibold">{{ avgOrderTime }}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-sm text-muted-foreground">Ochiq buyurtmalar</span>
            <span class="text-sm font-semibold">{{ orders.open.length }}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-sm text-muted-foreground">Bugun yetkazildi</span>
            <span class="text-sm font-semibold">{{ orders.delivered.length }}</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader class="pb-3">
          <CardTitle class="text-sm font-semibold flex items-center gap-2">
            <Wrench class="w-4 h-4 text-muted-foreground" />
            Texnik xizmat
          </CardTitle>
        </CardHeader>
        <CardContent class="space-y-3">
          <div class="flex justify-between items-center">
            <span class="text-sm text-muted-foreground">Ochiq muammolar</span>
            <span class="text-sm font-semibold">{{ maintenance.open.length }}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-sm text-muted-foreground">Tayinlangan</span>
            <span class="text-sm font-semibold">{{ maintenance.mine.length }}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
