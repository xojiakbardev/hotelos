<script setup lang="ts">
import { useToastStore } from '@/stores/toast'
import { cn } from '@/lib/utils'

const toast = useToastStore()

function dotColor(kind: string) {
  if (kind === 'success') return 'bg-green-500'
  if (kind === 'error') return 'bg-destructive'
  if (kind === 'warning') return 'bg-amber-500'
  return 'bg-primary'
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed top-5 right-5 z-[1000] pointer-events-none max-w-[440px]" aria-live="polite" aria-atomic="false">
      <TransitionGroup name="toast" tag="div" class="flex flex-col gap-2">
        <article
          v-for="item in toast.items"
          :key="item.id"
          class="pointer-events-auto flex items-start gap-2.5 px-4 py-3 rounded-lg border bg-card shadow-md text-sm cursor-pointer transition-all"
          role="status"
          @click="toast.dismiss(item.id)"
        >
          <span :class="cn('w-2 h-2 rounded-full mt-1.5 shrink-0', dotColor(item.kind))" aria-hidden="true" />
          <span class="flex-1 leading-snug">{{ item.message }}</span>
        </article>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-from { opacity: 0; transform: translateX(20px); }
.toast-enter-active, .toast-leave-active {
  transition: opacity 150ms ease, transform 150ms ease;
}
.toast-leave-to { opacity: 0; transform: translateX(20px); }
</style>
