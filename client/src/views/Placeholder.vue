<script setup lang="ts">
import { useRoute } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
const route = useRoute()
</script>

<template>
  <div class="page">
    <PageHeader
      :title="(route.meta.title as string) || (route.name as string)"
      description="Ushbu sahifa keyingi iteratsiyada to‘ldiriladi."
    />
    <article class="card-paper empty">
      Hozircha bu sahifa bo‘sh. Yaqinda funksional qism qo‘shiladi.
    </article>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.empty {
  padding: 48px;
  text-align: center;
  color: var(--muted-fg);
}
</style>
