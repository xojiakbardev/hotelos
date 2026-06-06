<script setup lang="ts">
import { ref, watch, type Component } from 'vue'

const props = withDefaults(defineProps<{
  label: string
  value: string | number
  icon?: Component
  iconColor?: 'primary' | 'success' | 'warning' | 'destructive' | 'muted'
  animate?: boolean
}>(), {
  iconColor: 'primary',
  animate: false,
})

const animating = ref(false)

watch(() => props.value, () => {
  if (props.animate) {
    animating.value = true
    setTimeout(() => { animating.value = false }, 300)
  }
})

const iconBgMap: Record<string, string> = {
  primary: 'bg-primary/[0.08]',
  success: 'bg-[hsl(var(--success))]/[0.08]',
  warning: 'bg-[hsl(var(--warning))]/[0.08]',
  destructive: 'bg-destructive/[0.08]',
  muted: 'bg-muted',
}

const iconColorMap: Record<string, string> = {
  primary: 'text-primary',
  success: 'text-[hsl(var(--success))]',
  warning: 'text-[hsl(var(--warning))]',
  destructive: 'text-destructive',
  muted: 'text-muted-foreground',
}
</script>

<template>
  <div
    class="rounded-lg border border-border bg-card p-4 transition-all duration-150 hover:shadow-sm hover:border-primary/20"
  >
    <div class="flex items-center justify-between">
      <div class="space-y-1">
        <p class="text-xs text-muted-foreground">{{ label }}</p>
        <p
          class="text-2xl font-bold tracking-tighter tabular-nums"
          :class="{ 'animate-count-up': animating }"
        >
          {{ value }}
        </p>
      </div>
      <div
        v-if="icon"
        class="h-8 w-8 rounded-lg grid place-items-center"
        :class="iconBgMap[iconColor]"
      >
        <component :is="icon" class="w-4 h-4" :class="iconColorMap[iconColor]" />
      </div>
    </div>
  </div>
</template>
