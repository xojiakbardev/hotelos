<script setup lang="ts">
/**
 * MenuList is now handled inside OrdersList.vue (menu tab).
 * This page redirects there.
 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
onMounted(() => router.replace('/orders'))
</script>

<template>
  <div class="text-center py-12 text-muted-foreground">Redirecting...</div>
</template>
