<script lang="ts">
import { cva, type VariantProps } from 'class-variance-authority'

export const sheetVariants = cva(
  'fixed z-50 gap-4 bg-background p-6 shadow-lg transition ease-in-out',
  {
    variants: {
      side: {
        top: 'inset-x-0 top-0 border-b',
        bottom: 'inset-x-0 bottom-0 border-t',
        left: 'inset-y-0 left-0 h-full w-3/4 border-r sm:max-w-sm',
        right: 'inset-y-0 right-0 h-full w-3/4 border-l sm:max-w-sm',
      },
    },
    defaultVariants: {
      side: 'right',
    },
  }
)

export type SheetVariants = VariantProps<typeof sheetVariants>
</script>

<script setup lang="ts">
import { type HTMLAttributes, computed } from 'vue'
import { DialogClose, DialogContent, type DialogContentEmits, type DialogContentProps, DialogOverlay, DialogPortal, useForwardPropsEmits } from 'radix-vue'
import { X } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

interface Props extends DialogContentProps {
  class?: HTMLAttributes['class']
  side?: SheetVariants['side']
}

const props = withDefaults(defineProps<Props>(), {
  side: 'left',
})
const emits = defineEmits<DialogContentEmits>()

const delegatedProps = computed(() => {
  const { class: _, side: __, ...delegated } = props
  return delegated
})
const forwarded = useForwardPropsEmits(delegatedProps, emits)
</script>

<template>
  <DialogPortal>
    <DialogOverlay class="fixed inset-0 z-50 bg-black/80 transition-opacity" />
    <DialogContent
      :class="cn(sheetVariants({ side }), props.class)"
      v-bind="forwarded"
    >
      <slot />
      <DialogClose class="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-secondary">
        <X class="w-4 h-4" />
      </DialogClose>
    </DialogContent>
  </DialogPortal>
</template>
