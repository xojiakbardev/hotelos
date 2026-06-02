<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    padding?: 'none' | 'sm' | 'md' | 'lg'
    interactive?: boolean
    glow?: boolean
  }>(),
  { padding: 'md', interactive: false, glow: false }
)
</script>

<template>
  <div
    :class="[
      glow ? 'glow-card' : 'card-paper',
      `pad-${padding}`,
      { 'card--interactive': interactive }
    ]"
  >
    <slot />
  </div>
</template>

<style scoped>
.pad-none { padding: 0; }
.pad-sm   { padding: 12px; }
.pad-md   { padding: 16px; }
.pad-lg   { padding: 24px; }

.card--interactive {
  cursor: pointer;
  transition: transform var(--motion-fast) var(--motion-ease),
              box-shadow var(--motion-fast) var(--motion-ease);
}
.card--interactive:hover { transform: translateY(-1px); box-shadow: var(--elev-2); }
</style>
