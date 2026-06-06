<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  score: number // 0 to 1
}>()

const widthPercent = computed(() => Math.max(0, Math.min(100, props.score * 100)))

const barColor = computed(() => {
  if (props.score >= 0.7) return 'bg-green-500'
  if (props.score >= 0.4) return 'bg-amber-500'
  return 'bg-red-500'
})
</script>

<template>
  <div class="w-full h-1 rounded-full bg-muted overflow-hidden">
    <div
      class="h-full rounded-full transition-all duration-300"
      :class="barColor"
      :style="{ width: widthPercent + '%' }"
    />
  </div>
</template>
