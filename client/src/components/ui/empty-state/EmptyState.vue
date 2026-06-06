<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  icon?: Component
  title: string
  description?: string
  actionLabel?: string
  actionFn?: () => void
}>()
</script>

<template>
  <div class="flex flex-col items-center justify-center py-12 px-4 text-center">
    <div v-if="icon" class="mb-4">
      <component :is="icon" class="w-16 h-16 text-muted-foreground/40" />
    </div>
    <h3 class="text-sm font-medium text-foreground mb-1">{{ title }}</h3>
    <p v-if="description" class="text-xs text-muted-foreground max-w-xs">
      {{ description }}
    </p>
    <button
      v-if="actionLabel && actionFn"
      class="mt-4 inline-flex items-center rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-foreground hover:bg-accent transition-colors duration-150"
      @click="actionFn"
    >
      {{ actionLabel }}
    </button>
  </div>
</template>
