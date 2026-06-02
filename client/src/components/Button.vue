<script setup lang="ts">
import { computed } from 'vue'

type Variant =
  | 'primary' | 'success' | 'destructive' | 'warning' | 'info'
  | 'outline' | 'secondary' | 'ghost' | 'link'
type Size = 'sm' | 'md' | 'lg' | 'icon'

const props = withDefaults(
  defineProps<{
    variant?: Variant
    size?: Size
    type?: 'button' | 'submit' | 'reset'
    disabled?: boolean
    loading?: boolean
  }>(),
  { variant: 'primary', size: 'md', type: 'button', disabled: false, loading: false }
)

const emit = defineEmits<{ click: [MouseEvent] }>()

const klass = computed(() => `btn btn--${props.variant} btn--${props.size}`)
</script>

<template>
  <button
    :type="type"
    :class="klass"
    :disabled="disabled || loading"
    @click="emit('click', $event)"
  >
    <span v-if="loading" class="spin" aria-hidden="true" />
    <slot />
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  white-space: nowrap;
  font-weight: 600;
  letter-spacing: -0.01em;
  border-radius: 10px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--motion-ease),
              border-color var(--motion-fast) var(--motion-ease),
              color var(--motion-fast) var(--motion-ease),
              box-shadow var(--motion-fast) var(--motion-ease),
              transform var(--motion-fast) var(--motion-ease);
}
.btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--primary) 22%, transparent);
}
.btn:disabled { cursor: not-allowed; opacity: 0.55; }
.btn:active:not(:disabled) { transform: translateY(1px); }

/* Sizes */
.btn--sm   { height: 36px; padding: 0 14px; font-size: var(--font-size-sm); }
.btn--md   { height: 44px; padding: 0 20px; font-size: var(--font-size-sm); }
.btn--lg   { height: 48px; padding: 0 24px; font-size: var(--font-size-md); }
.btn--icon { width: 44px; height: 44px; padding: 0; }

/* Variants */
.btn--primary {
  background: var(--primary);
  color: white;
  box-shadow: var(--primary-shadow);
}
.btn--primary:hover:not(:disabled) { background: var(--primary-strong); }

.btn--success {
  background: var(--success);
  color: white;
  box-shadow: var(--success-shadow);
}
.btn--success:hover:not(:disabled) { filter: brightness(0.95); }

.btn--destructive {
  background: var(--danger);
  color: white;
  box-shadow: var(--danger-shadow);
}
.btn--destructive:hover:not(:disabled) { filter: brightness(0.95); }

.btn--warning {
  background: var(--warn);
  color: var(--warn-ink);
  box-shadow: 0 4px 14px -4px color-mix(in oklch, var(--warn) 50%, transparent);
}
.btn--warning:hover:not(:disabled) { filter: brightness(0.96); }

.btn--info {
  background: var(--info);
  color: white;
  box-shadow: 0 4px 14px -4px color-mix(in oklch, var(--info) 50%, transparent);
}
.btn--info:hover:not(:disabled) { filter: brightness(0.95); }

.btn--outline {
  background: var(--surface);
  color: var(--foreground);
  border-color: var(--border);
}
.btn--outline:hover:not(:disabled) {
  border-color: color-mix(in oklch, var(--primary) 40%, var(--border));
  background: color-mix(in oklch, var(--primary) 4%, var(--surface));
}

.btn--secondary {
  background: var(--bg-subtle);
  color: var(--ink-700);
  border-color: var(--border);
}
.btn--secondary:hover:not(:disabled) {
  background: var(--primary-soft-2);
  color: var(--primary-strong);
}

.btn--ghost {
  background: transparent;
  color: var(--ink-500);
}
.btn--ghost:hover:not(:disabled) {
  background: var(--bg-subtle);
  color: var(--foreground);
}

.btn--link {
  background: transparent;
  color: var(--primary);
  padding: 0;
  height: auto;
  border-radius: 0;
}
.btn--link:hover:not(:disabled) { text-decoration: underline; }

.spin {
  width: 14px; height: 14px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 700ms linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
