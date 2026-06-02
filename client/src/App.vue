<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useWsStore } from '@/stores/ws'
import Toast from '@/components/Toast.vue'

const auth = useAuthStore()
const ws = useWsStore()

onMounted(() => {
  auth.restoreFromStorage()
  if (auth.token) ws.connect(auth.token)
})
</script>

<template>
  <RouterView />
  <Toast />
</template>
