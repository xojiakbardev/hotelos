<script setup lang="ts">
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
</script>

<template>
  <Teleport to="body">
    <div class="toast-stack" aria-live="polite" aria-atomic="false">
      <TransitionGroup name="toast" tag="div" class="toast-inner">
        <article
          v-for="item in toast.items"
          :key="item.id"
          :class="['toast', `toast--${item.kind}`]"
          role="status"
          @click="toast.dismiss(item.id)"
        >
          <span class="toast-dot" aria-hidden="true" />
          <span class="toast-msg">{{ item.message }}</span>
        </article>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-stack {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: var(--z-toast);
  pointer-events: none;
  max-width: min(440px, calc(100vw - 40px));
}
.toast-inner { display: flex; flex-direction: column; gap: 8px; }

.toast {
  pointer-events: auto;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  background: var(--surface);
  box-shadow: var(--elev-2);
  font-size: var(--font-size-sm);
  color: var(--foreground);
  cursor: pointer;
}
.toast-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex: 0 0 8px;
  background: var(--info);
}
.toast--success .toast-dot { background: var(--success); }
.toast--warning .toast-dot { background: var(--warn); }
.toast--error   .toast-dot { background: var(--danger); }

.toast-msg { flex: 1; line-height: 1.4; }

.toast-enter-from { opacity: 0; transform: translateX(20px); }
.toast-enter-active, .toast-leave-active {
  transition: opacity var(--motion-fast) var(--motion-ease),
              transform var(--motion-fast) var(--motion-ease);
}
.toast-leave-to { opacity: 0; transform: translateX(20px); }
</style>
