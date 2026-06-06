<script setup lang="ts">
import { useTheme } from '@/composables/useTheme'
import { Sun, Moon, Monitor } from 'lucide-vue-next'

const { theme, toggleTheme } = useTheme()
</script>

<template>
  <button
    class="inline-flex items-center justify-center w-8 h-8 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-all duration-150"
    :title="`Mavzuni o'zgartirish (${theme})`"
    @click="toggleTheme"
  >
    <Sun v-if="theme === 'light'" class="w-4 h-4" />
    <Moon v-else-if="theme === 'dark'" class="w-4 h-4" />
    <Monitor v-else class="w-4 h-4" />
  </button>
</template>
