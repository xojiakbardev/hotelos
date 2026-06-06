<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BlankLayout from '@/layouts/BlankLayout.vue'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { ThemeToggle } from '@/components/ui/theme-toggle'
import { useAuthStore } from '@/stores/auth'
import { useWsStore } from '@/stores/ws'
import { Loader2 } from 'lucide-vue-next'

const auth = useAuthStore()
const ws = useWsStore()
const route = useRoute()
const router = useRouter()

const phone = ref('')
const password = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const shaking = ref(false)

const demoUsers = [
  { role: 'Manager', phone: '+998901111111', password: 'manager123' },
  { role: 'Reception', phone: '+998902222222', password: 'reception123' },
  { role: 'Technician', phone: '+998903333333', password: 'technician123' },
  { role: 'Cleaner', phone: '+998904444444', password: 'cleaner123' },
  { role: 'Kitchen', phone: '+998905555555', password: 'kitchen123' },
]

function fillCredentials(u: { phone: string; password: string }) {
  phone.value = u.phone
  password.value = u.password
}

async function submit() {
  error.value = null
  loading.value = true
  try {
    await auth.login(phone.value.trim(), password.value)
    if (auth.token) ws.connect(auth.token)
    if (auth.role === 'guest') {
      if (auth.mustChangePassword) {
        router.replace('/guest/change-password')
      } else {
        router.replace('/guest')
      }
    } else {
      const next = (route.query.next as string) || '/'
      // Roles that don't have dashboard access — send them to their home
      if (next === '/' && auth.role === 'kitchen') {
        router.replace('/orders')
      } else if (next === '/' && auth.role === 'technician') {
        router.replace('/maintenance')
      } else if (next === '/' && auth.role === 'cleaner') {
        router.replace('/housekeeping')
      } else {
        router.replace(next)
      }
    }
  } catch (e: unknown) {
    const err = e as {
      response?: {
        data?: {
          error?: string
          message?: string
          details?: { loc?: (string | number)[]; msg?: string; type?: string }[]
        }
      }
    }
    const data = err.response?.data
    if (data?.error === 'validation_error' && data.details?.length) {
      const first = data.details[0]
      const field = first.loc?.[first.loc.length - 1]
      if (field === 'phone') {
        error.value = "Telefon raqami noto'g'ri formatda. Masalan: +998901234567"
      } else if (field === 'password') {
        error.value = "Parol kamida 6 ta belgidan iborat bo'lishi kerak"
      } else {
        error.value = first.msg || "Kiritilgan ma'lumotlar noto'g'ri"
      }
    } else if (data?.error === 'unauthenticated') {
      error.value = "Telefon yoki parol noto'g'ri"
    } else {
      error.value = data?.message ?? 'Tizimga kirishda xatolik yuz berdi'
    }
    // Shake animation on error
    shaking.value = true
    setTimeout(() => { shaking.value = false }, 300)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <BlankLayout>
    <!-- Theme toggle top-right -->
    <div class="fixed top-4 right-4 z-50">
      <ThemeToggle />
    </div>

    <Card
      class="w-full max-w-sm border-border/50 shadow-lg"
      :class="{ 'animate-shake': shaking }"
    >
        <CardHeader class="text-center space-y-2">
          <div class="mx-auto w-14 h-14 rounded-xl bg-primary text-primary-foreground grid place-items-center font-bold text-xl shadow-md">
            H
          </div>
          <CardTitle class="text-2xl tracking-tight">Tizimga kirish</CardTitle>
        </CardHeader>
        <CardContent>
          <form @submit.prevent="submit" class="space-y-4" novalidate>
            <div class="space-y-2">
              <Label for="phone">Telefon raqami</Label>
              <Input
                id="phone"
                v-model="phone"
                type="tel"
                autocomplete="username"
                inputmode="tel"
                placeholder="+998901234567"
                class="h-10"
                :disabled="loading"
              />
            </div>
            <div class="space-y-2">
              <Label for="password">Parol</Label>
              <Input
                id="password"
                v-model="password"
                type="password"
                autocomplete="current-password"
                placeholder="••••••••"
                class="h-10"
                :disabled="loading"
              />
            </div>

            <div
              v-if="error"
              class="rounded-lg border border-destructive/20 bg-destructive/5 text-destructive text-sm p-3 border-l-4 border-l-destructive"
              role="alert"
            >
              {{ error }}
            </div>

            <Button type="submit" class="w-full h-10" :disabled="loading">
              <Loader2 v-if="loading" class="w-4 h-4 mr-2 animate-spin" />
              {{ loading ? 'Kirilmoqda…' : 'Kirish' }}
            </Button>
          </form>
        </CardContent>
        <CardFooter class="flex-col gap-3">
          <Separator />
          <div class="space-y-2">
            <div class="flex gap-2">
              <button
                v-for="u in demoUsers.slice(0, 2)"
                :key="u.role"
                type="button"
                class="flex-1 inline-flex items-center justify-center rounded-full px-3 py-1 text-xs font-medium bg-muted text-muted-foreground hover:bg-accent hover:text-foreground hover:shadow-xs transition-all duration-150 cursor-pointer"
                @click="fillCredentials(u)"
              >
                {{ u.role }}
              </button>
            </div>
            <div class="flex gap-2">
              <button
                v-for="u in demoUsers.slice(2)"
                :key="u.role"
                type="button"
                class="flex-1 inline-flex items-center justify-center rounded-full px-3 py-1 text-xs font-medium bg-muted text-muted-foreground hover:bg-accent hover:text-foreground hover:shadow-xs transition-all duration-150 cursor-pointer"
                @click="fillCredentials(u)"
              >
                {{ u.role }}
              </button>
            </div>
          </div>
        </CardFooter>
      </Card>
  </BlankLayout>
</template>
