<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  hint?: string
  tone?: 'neutral' | 'primary' | 'success' | 'warn' | 'danger'
}>()
</script>

<template>
  <article :class="['stat', `stat--${tone ?? 'neutral'}`]">
    <div class="stat-label">{{ label }}</div>
    <div class="stat-value tabular">{{ value }}</div>
    <div v-if="hint" class="stat-hint">{{ hint }}</div>
  </article>
</template>

<style scoped>
.stat {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  box-shadow: var(--elev-1);
  transition: box-shadow var(--motion-base) var(--motion-ease);
  position: relative;
  overflow: hidden;
}
.stat:hover { box-shadow: var(--elev-2); }

/* Soft accent ribbon top-right based on tone */
.stat::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 4px;
  height: 100%;
  background: var(--accent, transparent);
}
.stat--primary  { --accent: var(--primary); }
.stat--success  { --accent: var(--success); }
.stat--warn     { --accent: var(--warn-ink); }
.stat--danger   { --accent: var(--danger); }

.stat-label {
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted-fg);
  font-weight: 600;
}
.stat-value {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  color: var(--ink-900);
  letter-spacing: -0.022em;
  line-height: 1.1;
}
.stat-hint {
  font-size: var(--font-size-xs);
  color: var(--muted-fg);
}
</style>
