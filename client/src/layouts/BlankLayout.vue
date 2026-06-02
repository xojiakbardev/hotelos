<script setup lang="ts"></script>

<template>
  <main class="blank">
    <slot />
  </main>
</template>

<style scoped>
.blank {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background:
    radial-gradient(1200px 600px at 80% -10%, color-mix(in oklch, var(--primary) 8%, transparent), transparent 60%),
    radial-gradient(900px 500px at 10% 110%, color-mix(in oklch, var(--primary) 6%, transparent), transparent 60%),
    var(--bg);
  padding: var(--space-lg);
}
</style>
