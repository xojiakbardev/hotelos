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
    await auth.login(phone.value, password.value)
    if (auth.token) ws.connect(auth.token)
    const next = (route.query.next as string) || '/'
    router.replace(next)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { message?: string } } }
    error.value = err.response?.data?.message ?? 'Telefon yoki parol noto‘g‘ri'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <BlankLayout>
    <form class="card" @submit.prevent="submit" novalidate>
      <div class="brand">
        <span class="brand-mark">H</span>
        <span class="brand-name">HotelOS</span>
      </div>

      <h1 class="title">Tizimga kirish</h1>
      <p class="subtitle">Xodimlar uchun boshqaruv paneli</p>

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

      <p class="hint">
        Demo akkauntlar test maqsadida <code>.env</code> fayliga yozilgan.
      </p>
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

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}
.brand-mark {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--primary);
  color: white;
  display: grid;
  place-items: center;
  font-weight: 700;
  font-family: var(--font-display);
  box-shadow: var(--primary-shadow);
}
.brand-name {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 600;
  color: var(--ink-900);
}

.title {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.022em;
  color: var(--ink-900);
  margin-top: 8px;
}
.subtitle {
  margin: 0 0 12px 0;
  color: var(--muted-fg);
  font-size: var(--font-size-sm);
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

.hint {
  margin: 8px 0 0 0;
  text-align: center;
  font-size: var(--font-size-xs);
  color: var(--muted-fg);
}
code {
  background: var(--bg-subtle);
  padding: 1px 6px;
  border-radius: var(--radius-xs);
  font-family: var(--font-mono);
  font-size: 0.92em;
}
</style>
