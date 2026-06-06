<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { DoorOpen, LogOut } from 'lucide-vue-next'

const auth = useAuthStore()
const router = useRouter()

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen bg-background">
    <header class="h-14 bg-primary text-primary-foreground flex items-center justify-between px-4 md:px-6">
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2">
          <DoorOpen class="w-5 h-5" />
          <span class="font-bold text-xl tracking-tight">{{ auth.user?.room_number }}</span>
        </div>
        <span class="text-sm opacity-80 hidden sm:inline">{{ auth.user?.full_name || 'Mehmon' }}</span>
      </div>
      <Button
        variant="ghost"
        size="sm"
        class="text-primary-foreground hover:bg-white/20 hover:text-primary-foreground gap-2"
        @click="logout"
      >
        <LogOut class="w-4 h-4" />
        Chiqish
      </Button>
    </header>
    <main class="max-w-3xl mx-auto p-4 md:p-6">
      <router-view />
    </main>
  </div>
</template>
