<script setup lang="ts">
import { RouterLink } from 'vue-router'
import BlankLayout from '@/layouts/BlankLayout.vue'
import Button from '@/components/Button.vue'
</script>

<template>
  <BlankLayout>
    <div class="card-paper card">
      <h1 class="code">404</h1>
      <p class="msg">Bu sahifa mavjud emas yoki o‘chirilgan.</p>
      <RouterLink to="/" custom v-slot="{ navigate }">
        <Button variant="primary" size="md" @click="navigate">Bosh sahifaga qaytish</Button>
      </RouterLink>
    </div>
  </BlankLayout>
</template>

<style scoped>
.card {
  text-align: center;
  padding: 48px 56px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.code {
  font-family: var(--font-display);
  font-size: 64px;
  font-weight: 700;
  color: var(--ink-900);
  letter-spacing: -0.04em;
}
.msg { margin: 0; color: var(--muted-fg); font-size: var(--font-size-sm); }
</style>
