<script setup lang="ts">
/**
 * Daily guest check-in line chart.
 *
 * Fetches `/api/reception/guests/stats/daily?days=<N>` on mount and renders
 * a smooth SVG line + area gradient. Refetches on incoming guest-related
 * WebSocket events so a fresh check-in lights up the chart in real time.
 */
import { computed, onMounted, watch, ref } from 'vue'
import { receptionApi, type DailyCount } from '@/api/reception'
import { useWsStore } from '@/stores/ws'

const props = withDefaults(
  defineProps<{ days?: number; height?: number }>(),
  { days: 30, height: 200 }
)

const ws = useWsStore()
const data = ref<DailyCount[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    data.value = await receptionApi.dailyGuestStats(props.days)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { message?: string } }; message?: string }
    error.value = err.response?.data?.message ?? err.message ?? 'Yuklanmadi'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(
  () => ws.lastEvent,
  (env) => { if (env?.channel?.startsWith('guests.')) load() }
)

// ---- Aggregates shown next to the title ----

const totalInWindow = computed(() => data.value.reduce((a, b) => a + b.count, 0))
const peakInWindow = computed(() => data.value.reduce((a, b) => Math.max(a, b.count), 0))
const avgPerDay = computed(() =>
  data.value.length === 0 ? 0 : Math.round((totalInWindow.value / data.value.length) * 10) / 10
)
const maxY = computed(() => Math.max(3, peakInWindow.value + 1))

// ---- SVG geometry ----

const VB_W = 800
const VB_H = 220
const PAD = { top: 16, right: 20, bottom: 30, left: 36 }
const innerW = VB_W - PAD.left - PAD.right
const innerH = VB_H - PAD.top - PAD.bottom

function xFor(idx: number): number {
  const n = data.value.length
  if (n <= 1) return PAD.left
  return PAD.left + (idx * innerW) / (n - 1)
}
function yFor(value: number): number {
  return PAD.top + innerH - (value / maxY.value) * innerH
}

const linePoints = computed(() =>
  data.value.map((d, i) => `${xFor(i)},${yFor(d.count)}`).join(' ')
)

const areaPath = computed(() => {
  if (!data.value.length) return ''
  const baseline = PAD.top + innerH
  let d = `M ${xFor(0)},${baseline}`
  for (let i = 0; i < data.value.length; i++) {
    d += ` L ${xFor(i)},${yFor(data.value[i].count)}`
  }
  d += ` L ${xFor(data.value.length - 1)},${baseline} Z`
  return d
})

// ---- Axis ticks ----

interface YTick { y: number; v: number }
const yTicks = computed<YTick[]>(() => {
  const steps = 4
  const arr: YTick[] = []
  for (let i = 0; i <= steps; i++) {
    const v = Math.round((maxY.value * i) / steps)
    arr.push({ y: yFor(v), v })
  }
  return arr
})

interface XTick { x: number; label: string }
function formatDay(iso: string): string {
  // "YYYY-MM-DD" → "DD/MM"
  const d = new Date(iso + 'T00:00:00Z')
  const dd = String(d.getUTCDate()).padStart(2, '0')
  const mm = String(d.getUTCMonth() + 1).padStart(2, '0')
  return `${dd}.${mm}`
}
const xTicks = computed<XTick[]>(() => {
  const n = data.value.length
  if (n === 0) return []
  const positions = [0, Math.round((n - 1) * 0.25), Math.round((n - 1) * 0.5), Math.round((n - 1) * 0.75), n - 1]
  return positions.map((i) => ({ x: xFor(i), label: formatDay(data.value[i].date) }))
})

const isEmpty = computed(() => !loading.value && data.value.length > 0 && totalInWindow.value === 0)
</script>

<template>
  <article class="card-paper chart">
    <header class="chart-head">
      <div class="title-block">
        <h2 class="title">Mehmonlar oqimi</h2>
        <p class="subtitle">So‘nggi {{ days }} kun ichida qabul qilingan mehmonlar</p>
      </div>
      <div class="metrics">
        <div class="metric">
          <div class="metric-value tabular">{{ totalInWindow }}</div>
          <div class="metric-label">Jami</div>
        </div>
        <div class="metric">
          <div class="metric-value tabular">{{ peakInWindow }}</div>
          <div class="metric-label">Eng ko‘p/kun</div>
        </div>
        <div class="metric">
          <div class="metric-value tabular">{{ avgPerDay }}</div>
          <div class="metric-label">O‘rtacha/kun</div>
        </div>
      </div>
    </header>

    <div v-if="error" class="error">{{ error }}</div>

    <div class="canvas" :style="{ height: `${height}px` }">
      <svg
        :viewBox="`0 0 ${VB_W} ${VB_H}`"
        preserveAspectRatio="none"
        class="svg"
        role="img"
        aria-label="Kunlik mehmonlar chizmasi"
      >
        <defs>
          <linearGradient id="guestsAreaFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="var(--primary)" stop-opacity="0.32" />
            <stop offset="100%" stop-color="var(--primary)" stop-opacity="0" />
          </linearGradient>
        </defs>

        <g class="grid">
          <line
            v-for="(t, i) in yTicks"
            :key="`gy-${i}`"
            :x1="PAD.left"
            :x2="VB_W - PAD.right"
            :y1="t.y"
            :y2="t.y"
          />
          <text
            v-for="(t, i) in yTicks"
            :key="`ly-${i}`"
            :x="PAD.left - 8"
            :y="t.y + 4"
            text-anchor="end"
            class="tick-y"
          >{{ t.v }}</text>
        </g>

        <path v-if="data.length" :d="areaPath" fill="url(#guestsAreaFill)" />

        <polyline
          v-if="data.length"
          :points="linePoints"
          fill="none"
          stroke="var(--primary)"
          stroke-width="2.2"
          stroke-linejoin="round"
          stroke-linecap="round"
        />

        <g v-if="data.length" class="dots">
          <circle
            v-for="(d, i) in data"
            v-show="d.count > 0"
            :key="`d-${i}`"
            :cx="xFor(i)"
            :cy="yFor(d.count)"
            r="3"
            fill="var(--surface)"
            stroke="var(--primary)"
            stroke-width="1.8"
          />
        </g>

        <g class="x-labels">
          <text
            v-for="(t, i) in xTicks"
            :key="`tx-${i}`"
            :x="t.x"
            :y="VB_H - 8"
            text-anchor="middle"
            class="tick-x"
          >{{ t.label }}</text>
        </g>
      </svg>

      <div v-if="loading && !data.length" class="overlay">Yuklanmoqda…</div>
      <div v-else-if="isEmpty" class="overlay">
        So‘nggi {{ days }} kun ichida qabul qilingan mehmonlar yo‘q
      </div>
    </div>
  </article>
</template>

<style scoped>
.chart { display: flex; flex-direction: column; gap: 14px; padding: 18px 20px 14px; }

.chart-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}
.title-block { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.title {
  font-family: var(--font-display);
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--ink-900);
  letter-spacing: -0.015em;
}
.subtitle { margin: 0; font-size: var(--font-size-xs); color: var(--muted-fg); }

.metrics { display: flex; gap: 22px; align-items: stretch; }
.metric { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
.metric-value {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 22px;
  color: var(--ink-900);
  line-height: 1;
  letter-spacing: -0.02em;
}
.metric-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted-fg);
  font-weight: 600;
}

.error {
  padding: 10px 14px;
  background: color-mix(in srgb, var(--danger) 10%, transparent);
  color: var(--danger);
  border-radius: 10px;
  font-size: var(--font-size-sm);
}

.canvas { position: relative; width: 100%; }
.svg { width: 100%; height: 100%; display: block; }

.svg .grid line {
  stroke: var(--border);
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
}
.svg .tick-y, .svg .tick-x {
  font-family: var(--font-sans);
  font-size: 11px;
  fill: var(--muted-fg);
  font-weight: 500;
}

.overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--muted-fg);
  font-size: var(--font-size-sm);
  pointer-events: none;
}
</style>
