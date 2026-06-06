<script setup lang="ts">
export type StatusBadgeVariant = 'success' | 'warning' | 'destructive' | 'default' | 'secondary'

withDefaults(defineProps<{
  variant: StatusBadgeVariant
  label: string
  pulse?: boolean
}>(), {
  pulse: false,
})

const variantClasses: Record<StatusBadgeVariant, string> = {
  success: 'text-green-600 bg-green-500/[var(--badge-bg-opacity)] dark:text-green-400',
  warning: 'text-amber-600 bg-amber-500/[var(--badge-bg-opacity)] dark:text-amber-400',
  destructive: 'text-red-600 bg-red-500/[var(--badge-bg-opacity)] dark:text-red-400',
  default: 'text-primary bg-primary/[var(--badge-bg-opacity)]',
  secondary: 'text-muted-foreground bg-muted',
}
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium h-6"
    :class="variantClasses[variant]"
  >
    <span
      v-if="pulse"
      class="w-1.5 h-1.5 rounded-full animate-pulse-dot"
      :class="{
        'bg-green-500': variant === 'success',
        'bg-amber-500': variant === 'warning',
        'bg-red-500': variant === 'destructive',
        'bg-primary': variant === 'default',
        'bg-muted-foreground': variant === 'secondary',
      }"
    />
    {{ label }}
  </span>
</template>
