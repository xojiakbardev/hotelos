<script setup lang="ts">
import { type HTMLAttributes } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps<{ class?: HTMLAttributes['class'] }>()
</script>

<template>
  <span :class="cn('flex h-full w-full items-center justify-center rounded-full bg-muted text-sm font-medium', props.class)">
    <slot />
  </span>
</template>
