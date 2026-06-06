<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useWsStore } from '@/stores/ws'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Database,
  Server,
  Globe,
  Wifi,
  Monitor,
  ChefHat,
  Sparkles,
  Wrench,
  Shield,
  Radio,
} from 'lucide-vue-next'

const ws = useWsStore()

// Simulate health checks
interface ServiceStatus {
  name: string
  label: string
  icon: any
  color: string
  status: 'healthy' | 'checking' | 'error'
  lastPing: number
}

const services = ref<ServiceStatus[]>([
  { name: 'nginx', label: 'Nginx', icon: Globe, color: 'text-green-500', status: 'checking', lastPing: 0 },
  { name: 'auth', label: 'Auth', icon: Shield, color: 'text-blue-500', status: 'checking', lastPing: 0 },
  { name: 'reception', label: 'Reception', icon: Monitor, color: 'text-indigo-500', status: 'checking', lastPing: 0 },
  { name: 'housekeeping', label: 'Housekeeping', icon: Sparkles, color: 'text-amber-500', status: 'checking', lastPing: 0 },
  { name: 'room-service', label: 'Room Service', icon: ChefHat, color: 'text-orange-500', status: 'checking', lastPing: 0 },
  { name: 'maintenance', label: 'Maintenance', icon: Wrench, color: 'text-red-500', status: 'checking', lastPing: 0 },
  { name: 'ws-gateway', label: 'WS Gateway', icon: Wifi, color: 'text-purple-500', status: 'checking', lastPing: 0 },
  { name: 'postgres', label: 'PostgreSQL', icon: Database, color: 'text-sky-500', status: 'checking', lastPing: 0 },
  { name: 'redis', label: 'Redis', icon: Radio, color: 'text-rose-500', status: 'checking', lastPing: 0 },
])

// Animated data flow pulses
const pulses = ref<{ id: number; from: number; to: number; active: boolean }[]>([])
let pulseId = 0

function addPulse(from: number, to: number) {
  const id = pulseId++
  pulses.value.push({ id, from, to, active: true })
  setTimeout(() => {
    pulses.value = pulses.value.filter(p => p.id !== id)
  }, 1500)
}

// Simulate random event flow
let flowInterval: ReturnType<typeof setInterval> | null = null

function startFlow() {
  flowInterval = setInterval(() => {
    // Random data flows between services
    const flows = [
      [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [0, 6], // nginx → services
      [2, 7], [1, 7], [3, 7], [4, 7], [5, 7], // services → postgres
      [2, 8], [3, 8], [5, 8], [6, 8], // services → redis
      [8, 6], // redis → ws-gateway
    ]
    const pick = flows[Math.floor(Math.random() * flows.length)]
    addPulse(pick[0], pick[1])
  }, 800)
}

async function checkHealth() {
  const endpoints: Record<string, string> = {
    auth: '/api/auth/health',
    reception: '/api/reception/health',
    housekeeping: '/api/housekeeping/health',
    'room-service': '/api/room-service/health',
    maintenance: '/api/maintenance/health',
  }

  for (const svc of services.value) {
    const url = endpoints[svc.name]
    if (!url) {
      // nginx, postgres, redis — mark healthy if app loads
      svc.status = 'healthy'
      svc.lastPing = Date.now()
      continue
    }
    try {
      const start = Date.now()
      const res = await fetch(url)
      if (res.ok) {
        svc.status = 'healthy'
        svc.lastPing = Date.now() - start
      } else {
        svc.status = 'error'
      }
    } catch {
      svc.status = 'error'
    }
  }
}

const healthyCount = computed(() => services.value.filter(s => s.status === 'healthy').length)
const wsConnected = computed(() => ws.connected)
const lastEvent = computed(() => ws.lastEvent?.channel || '—')

onMounted(() => {
  checkHealth()
  startFlow()
})

onUnmounted(() => {
  if (flowInterval) clearInterval(flowInterval)
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header stats -->
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold tracking-tight">Infratuzilma</h2>
      <div class="flex items-center gap-3">
        <Badge :variant="wsConnected ? 'success' : 'destructive'">
          WS {{ wsConnected ? 'Ulangan' : 'Uzilgan' }}
        </Badge>
        <Badge variant="secondary">{{ healthyCount }}/{{ services.length }} sog'lom</Badge>
      </div>
    </div>

    <!-- Architecture visualization -->
    <Card class="p-6 overflow-hidden">
      <div class="relative" style="min-height: 500px;">
        <!-- Client (Browser) -->
        <div class="absolute left-1/2 top-0 -translate-x-1/2 flex flex-col items-center gap-1 z-10">
          <div class="w-14 h-14 rounded-xl bg-card border-2 border-primary/30 grid place-items-center shadow-sm animate-pulse-dot">
            <Monitor class="w-6 h-6 text-primary" />
          </div>
          <span class="text-[10px] font-medium text-muted-foreground">Browser</span>
        </div>

        <!-- Nginx (Gateway) -->
        <div class="absolute left-1/2 top-[80px] -translate-x-1/2 flex flex-col items-center gap-1 z-10">
          <div class="w-12 h-12 rounded-lg bg-green-500/10 border border-green-500/30 grid place-items-center">
            <Globe class="w-5 h-5 text-green-500" />
          </div>
          <span class="text-[10px] font-medium text-muted-foreground">Nginx :8080</span>
        </div>

        <!-- Connection line: Browser → Nginx -->
        <svg class="absolute left-1/2 top-[56px] -translate-x-1/2 z-0" width="2" height="24">
          <line x1="1" y1="0" x2="1" y2="24" stroke="currentColor" class="text-border" stroke-width="2" stroke-dasharray="4 4">
            <animate attributeName="stroke-dashoffset" from="8" to="0" dur="1s" repeatCount="indefinite" />
          </line>
        </svg>

        <!-- Services row -->
        <div class="absolute left-0 right-0 top-[160px] flex justify-center gap-4 flex-wrap px-4 z-10">
          <div
            v-for="(svc, i) in services.slice(1, 7)"
            :key="svc.name"
            class="flex flex-col items-center gap-1.5"
          >
            <div
              class="w-11 h-11 rounded-lg border grid place-items-center transition-all duration-300"
              :class="[
                svc.status === 'healthy' ? 'border-green-500/30 bg-green-500/5' :
                svc.status === 'error' ? 'border-red-500/30 bg-red-500/5' :
                'border-border bg-muted/50'
              ]"
            >
              <component :is="svc.icon" class="w-5 h-5" :class="svc.color" />
            </div>
            <span class="text-[9px] font-medium text-muted-foreground text-center leading-tight">{{ svc.label }}</span>
            <div
              class="w-1.5 h-1.5 rounded-full"
              :class="svc.status === 'healthy' ? 'bg-green-500 animate-pulse-dot' : svc.status === 'error' ? 'bg-red-500' : 'bg-muted-foreground'"
            />
          </div>
        </div>

        <!-- Connection lines: Nginx → Services -->
        <svg class="absolute left-0 right-0 top-[125px] z-0" height="35" width="100%">
          <line x1="50%" y1="0" x2="50%" y2="35" stroke="currentColor" class="text-border" stroke-width="1.5" stroke-dasharray="3 3">
            <animate attributeName="stroke-dashoffset" from="6" to="0" dur="0.8s" repeatCount="indefinite" />
          </line>
        </svg>

        <!-- Data layer -->
        <div class="absolute left-0 right-0 top-[300px] z-10">
          <div class="flex justify-center items-center gap-2 mb-4">
            <div class="h-px flex-1 max-w-[100px] bg-border" />
            <span class="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Ma'lumotlar qatlami</span>
            <div class="h-px flex-1 max-w-[100px] bg-border" />
          </div>

          <div class="flex justify-center gap-12">
            <!-- PostgreSQL -->
            <div class="flex flex-col items-center gap-1.5">
              <div
                class="w-14 h-14 rounded-xl border-2 grid place-items-center"
                :class="services[7].status === 'healthy' ? 'border-sky-500/30 bg-sky-500/5' : 'border-border'"
              >
                <Database class="w-6 h-6 text-sky-500" />
              </div>
              <span class="text-[10px] font-medium text-muted-foreground">PostgreSQL</span>
              <span class="text-[9px] text-muted-foreground">6 schema</span>
              <div
                class="w-1.5 h-1.5 rounded-full"
                :class="services[7].status === 'healthy' ? 'bg-green-500 animate-pulse-dot' : 'bg-muted-foreground'"
              />
            </div>

            <!-- Redis -->
            <div class="flex flex-col items-center gap-1.5">
              <div
                class="w-14 h-14 rounded-xl border-2 grid place-items-center"
                :class="services[8].status === 'healthy' ? 'border-rose-500/30 bg-rose-500/5' : 'border-border'"
              >
                <Radio class="w-6 h-6 text-rose-500" />
              </div>
              <span class="text-[10px] font-medium text-muted-foreground">Redis</span>
              <span class="text-[9px] text-muted-foreground">Pub/Sub</span>
              <div
                class="w-1.5 h-1.5 rounded-full"
                :class="services[8].status === 'healthy' ? 'bg-green-500 animate-pulse-dot' : 'bg-muted-foreground'"
              />
            </div>
          </div>
        </div>

        <!-- Connection lines: Services → Data layer -->
        <svg class="absolute left-0 right-0 top-[260px] z-0" height="40" width="100%">
          <line x1="35%" y1="0" x2="35%" y2="40" stroke="currentColor" class="text-sky-500/30" stroke-width="1.5" stroke-dasharray="3 3">
            <animate attributeName="stroke-dashoffset" from="6" to="0" dur="1.2s" repeatCount="indefinite" />
          </line>
          <line x1="65%" y1="0" x2="65%" y2="40" stroke="currentColor" class="text-rose-500/30" stroke-width="1.5" stroke-dasharray="3 3">
            <animate attributeName="stroke-dashoffset" from="6" to="0" dur="0.9s" repeatCount="indefinite" />
          </line>
        </svg>

        <!-- Event flow visualization -->
        <div class="absolute left-0 right-0 top-[430px] z-10">
          <div class="flex justify-center items-center gap-2 mb-3">
            <div class="h-px flex-1 max-w-[100px] bg-border" />
            <span class="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Jonli eventlar</span>
            <div class="h-px flex-1 max-w-[100px] bg-border" />
          </div>
          <div class="flex justify-center">
            <div class="bg-muted/50 rounded-lg border px-4 py-2 flex items-center gap-3 min-w-[280px]">
              <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse-dot" />
              <div class="flex-1">
                <p class="text-xs font-mono text-foreground truncate">{{ lastEvent }}</p>
                <p class="text-[9px] text-muted-foreground">so'nggi event</p>
              </div>
              <Badge variant="secondary" class="text-[9px]">{{ ws.eventLog.length }}</Badge>
            </div>
          </div>
        </div>
      </div>
    </Card>

    <!-- Service details grid -->
    <div class="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-2">
      <div
        v-for="svc in services"
        :key="svc.name"
        class="flex flex-col items-center gap-1 p-2 rounded-lg border transition-all duration-200 hover:shadow-xs"
        :class="svc.status === 'healthy' ? 'border-green-500/20' : 'border-border'"
      >
        <component :is="svc.icon" class="w-4 h-4" :class="svc.color" />
        <span class="text-[9px] font-medium text-center leading-tight">{{ svc.label }}</span>
        <span
          class="text-[8px] font-mono"
          :class="svc.status === 'healthy' ? 'text-green-600' : 'text-muted-foreground'"
        >
          {{ svc.status === 'healthy' ? (svc.lastPing > 0 ? svc.lastPing + 'ms' : 'OK') : '...' }}
        </span>
      </div>
    </div>
  </div>
</template>
