<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Loader2 } from 'lucide-vue-next'

const auth = useAuthStore()
const router = useRouter()
const toast = useToastStore()

const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

async function submit() {
  error.value = null
  if (newPassword.value.length < 4) {
    error.value = "Yangi parol kamida 4 ta belgidan iborat bo'lishi kerak"
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    error.value = 'Parollar mos kelmaydi'
    return
  }
  loading.value = true
  try {
    await auth.changePassword(currentPassword.value, newPassword.value)
    toast.success("Parol muvaffaqiyatli o'zgartirildi")
    router.replace('/guest')
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.response?.data?.message
    error.value = msg || "Parolni o'zgartirishda xatolik"
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex items-center justify-center min-h-[60vh]">
    <Card class="w-full max-w-sm">
      <CardHeader>
        <CardTitle class="text-lg">Parolni o'zgartirish</CardTitle>
        <CardDescription v-if="auth.mustChangePassword">
          Xavfsizlik uchun birinchi kirishda parolingizni o'zgartiring.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form @submit.prevent="submit" class="space-y-4">
          <div class="space-y-2">
            <Label>Hozirgi parol (PIN)</Label>
            <Input v-model="currentPassword" type="password" required />
          </div>
          <div class="space-y-2">
            <Label>Yangi parol</Label>
            <Input v-model="newPassword" type="password" required />
          </div>
          <div class="space-y-2">
            <Label>Yangi parolni tasdiqlang</Label>
            <Input v-model="confirmPassword" type="password" required />
          </div>
          <div v-if="error" class="rounded-md bg-destructive/10 text-destructive text-sm p-3" role="alert">
            {{ error }}
          </div>
          <Button type="submit" class="w-full" :disabled="loading">
            <Loader2 v-if="loading" class="w-4 h-4 mr-2 animate-spin" />
            {{ loading ? "O'zgartirilmoqda…" : "Parolni o'zgartirish" }}
          </Button>
        </form>
      </CardContent>
    </Card>
  </div>
</template>
