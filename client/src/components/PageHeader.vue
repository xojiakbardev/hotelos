<script setup lang="ts">
defineProps<{ title: string }>()
</script>

<template>
  <header class="ph">
    <h1 class="ph-title">{{ title }}</h1>
    <div class="ph-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.ph {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  padding: 14px 18px;
  background: var(--surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  box-shadow: var(--elev-1);
}
.ph-title {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.015em;
  color: var(--ink-900);
}
.ph-actions { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; flex-shrink: 0; }
</style>
