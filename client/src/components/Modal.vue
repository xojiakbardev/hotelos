<script setup lang="ts">
/**
 * Generic modal shell.
 *
 * Used for every form in hotelos (check-in, new order, report issue,
 * add staff). Forms are NEVER routed to as separate pages — they always
 * open as a modal on the parent list page.
 *
 * Props
 *   open:   visibility (use v-model:open from parent)
 *   title:  modal header text
 *   size:   sm (420) / md (560) / lg (760)
 *
 * Slots
 *   default: modal body content (form fields, etc.)
 *   footer:  action buttons aligned to the right
 *
 * Events
 *   close:  fired on backdrop click, X click, or Esc
 */
import { onMounted, onUnmounted, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    size?: 'sm' | 'md' | 'lg'
    closeOnBackdrop?: boolean
  }>(),
  { size: 'md', closeOnBackdrop: true }
)

const emit = defineEmits<{ close: [] }>()

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.open) emit('close')
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

// Lock body scroll while the modal is open.
watch(
  () => props.open,
  (isOpen) => {
    document.body.style.overflow = isOpen ? 'hidden' : ''
  }
)
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="open"
        class="scrim"
        role="dialog"
        aria-modal="true"
        @click.self="closeOnBackdrop && emit('close')"
      >
        <div :class="['modal', `modal--${size}`]">
          <header class="modal-head">
            <h2 class="modal-title">{{ title }}</h2>
            <button class="close-x" type="button" :aria-label="`Yopish`" @click="emit('close')">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </header>

          <section class="modal-body">
            <slot />
          </section>

          <footer v-if="$slots.footer" class="modal-foot">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.scrim {
  position: fixed;
  inset: 0;
  background: rgba(15, 17, 21, 0.5);
  display: grid;
  place-items: center;
  z-index: var(--z-modal);
  padding: var(--space-md);
  backdrop-filter: blur(2px);
}

.modal {
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--elev-3);
  display: flex;
  flex-direction: column;
  max-height: calc(100dvh - 48px);
  overflow: hidden;
}
.modal--sm { max-width: 420px; }
.modal--md { max-width: 560px; }
.modal--lg { max-width: 760px; }

.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border);
}
.modal-title {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.015em;
  color: var(--ink-900);
}

.close-x {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  background: transparent;
  color: var(--ink-500);
  border: 1px solid transparent;
  border-radius: 8px;
  transition: background var(--motion-fast) var(--motion-ease), color var(--motion-fast) var(--motion-ease);
}
.close-x:hover { background: var(--bg-subtle); color: var(--ink-800); }

.modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1 1 auto;
}

.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 20px;
  border-top: 1px solid var(--border);
  background: var(--bg-subtle);
}

.modal-enter-from .modal,
.modal-leave-to .modal { opacity: 0; transform: scale(0.96); }
.modal-enter-from,
.modal-leave-to { opacity: 0; }
.modal-enter-active,
.modal-leave-active { transition: opacity var(--motion-fast) var(--motion-ease); }
.modal-enter-active .modal,
.modal-leave-active .modal { transition: opacity var(--motion-base) var(--motion-ease), transform var(--motion-base) var(--motion-ease); }
</style>
