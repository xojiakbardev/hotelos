<script setup lang="ts">
/**
 * Tasdiqlash dialogi — qisqa harakatlar uchun (o'chirish, jo'natish, claim).
 * Forma uchun ishlatilmaydi — formalar alohida route'da bo'ladi.
 */
import Button from './Button.vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    message?: string
    confirmLabel?: string
    cancelLabel?: string
    tone?: 'primary' | 'destructive'
    pending?: boolean
  }>(),
  { confirmLabel: 'Tasdiqlash', cancelLabel: 'Bekor qilish', tone: 'primary', pending: false }
)

const emit = defineEmits<{ confirm: []; cancel: [] }>()
</script>

<template>
  <Teleport to="body">
    <Transition name="scrim">
      <div
        v-if="props.open"
        class="scrim"
        role="dialog"
        aria-modal="true"
        @click.self="emit('cancel')"
      >
        <div class="dlg">
          <h2 class="dlg-title">{{ props.title }}</h2>
          <p v-if="props.message" class="dlg-msg">{{ props.message }}</p>
          <div class="dlg-foot">
            <Button variant="ghost" :disabled="pending" @click="emit('cancel')">
              {{ props.cancelLabel }}
            </Button>
            <Button
              :variant="props.tone === 'destructive' ? 'destructive' : 'primary'"
              :loading="pending"
              @click="emit('confirm')"
            >
              {{ pending ? 'Bajarilmoqda…' : props.confirmLabel }}
            </Button>
          </div>
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
.dlg {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  max-width: 440px;
  width: 100%;
  box-shadow: var(--elev-3);
  animation: pop-in 220ms var(--motion-ease);
}
.dlg-title {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--ink-900);
  letter-spacing: -0.015em;
}
.dlg-msg {
  color: var(--muted-fg);
  margin: 0 0 22px 0;
  font-size: var(--font-size-sm);
  line-height: 1.5;
}
.dlg-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.scrim-enter-from, .scrim-leave-to { opacity: 0; }
.scrim-enter-active, .scrim-leave-active { transition: opacity var(--motion-fast) var(--motion-ease); }

@keyframes pop-in {
  from { opacity: 0; transform: scale(0.96); }
  to   { opacity: 1; transform: scale(1); }
}
</style>
