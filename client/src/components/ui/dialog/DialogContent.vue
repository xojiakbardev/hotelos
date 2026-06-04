<script setup lang="ts">
import { type HTMLAttributes, computed } from 'vue'
import {
  DialogClose,
  DialogContent,
  DialogOverlay,
  DialogPortal,
} from 'radix-vue'
import { X } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
  forceMount?: boolean
}>()
</script>

<template>
  <DialogPortal :force-mount="forceMount">
    <DialogOverlay class="fixed inset-0 z-50 bg-black/80" />
    <DialogContent
      :class="cn(
        'fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg sm:rounded-lg',
        props.class,
      )"
    >
      <slot />
      <DialogClose
        class="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none cursor-pointer"
      >
        <X class="w-4 h-4" />
      </DialogClose>
    </DialogContent>
  </DialogPortal>
</template>
