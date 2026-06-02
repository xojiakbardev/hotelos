<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BlankLayout from '@/layouts/BlankLayout.vue'
import Button from '@/components/Button.vue'
import { useAuthStore } from '@/stores/auth'
import { useWsStore } from '@/stores/ws'

const auth = useAuthStore()
const ws = useWsStore()
const route = useRoute()
const router = useRouter()

const phone = ref('')
const password = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

async function submit() {
  error.value = null
  loading.value = true
  try {
    await auth.login(phone.value.trim(), password.value)
    if (auth.token) ws.connect(auth.token)
    const next = (route.query.next as string) || '/'
    router.replace(next)
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
        error.value = 'Telefon raqami noto‘g‘ri formatda. Masalan: +998901234567'
      } else if (field === 'password') {
        error.value = 'Parol kamida 6 ta belgidan iborat bo‘lishi kerak'
      } else {
        error.value = first.msg || 'Kiritilgan ma’lumotlar noto‘g‘ri'
      }
    } else if (data?.error === 'unauthenticated') {
      error.value = 'Telefon yoki parol noto‘g‘ri'
    } else {
      error.value = data?.message ?? 'Tizimga kirishda xatolik yuz berdi'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <BlankLayout>
    <form class="card" @submit.prevent="submit" novalidate>
      <h1 class="title">Tizimga kirish</h1>

      <label class="field">
        <span>Telefon raqami</span>
        <input
          v-model="phone"
          type="tel"
          autocomplete="username"
          inputmode="tel"
          placeholder="+998901234567"
          required
        />
      </label>

      <label class="field">
        <span>Parol</span>
        <input
          v-model="password"
          type="password"
          autocomplete="current-password"
          placeholder="••••••••"
          required
          minlength="6"
        />
      </label>

      <p v-if="error" class="error" role="alert">{{ error }}</p>

      <Button type="submit" variant="primary" size="lg" :loading="loading">
        {{ loading ? 'Kirilmoqda…' : 'Kirish' }}
      </Button>
    </form>
  </BlankLayout>
</template>

<style scoped>
.card {
  width: 100%;
  max-width: 380px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--elev-2);
  padding: 32px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.022em;
  color: var(--ink-900);
  margin-bottom: 8px;
}

.field { display: flex; flex-direction: column; gap: 6px; font-size: var(--font-size-sm); }
.field > span { font-weight: 500; color: var(--ink-700); }
.field input {
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg);
  color: var(--foreground);
  font: inherit;
  font-size: var(--font-size-sm);
  transition: border-color var(--motion-fast) var(--motion-ease),
              box-shadow var(--motion-fast) var(--motion-ease);
}
.field input:focus {
  outline: none;
  border-color: color-mix(in oklch, var(--primary) 60%, var(--border));
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--primary) 18%, transparent);
}

.error {
  margin: 0;
  padding: 10px 14px;
  background: color-mix(in srgb, var(--danger) 10%, transparent);
  color: var(--danger);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
}
</style>
