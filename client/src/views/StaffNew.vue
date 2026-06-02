<script setup lang="ts">
/**
 * Embeddable "add staff" form. Mounted in a Modal from StaffList.
 */
import { computed, ref } from 'vue'
import Button from '@/components/Button.vue'
import { authApi, type Role, type UserOut } from '@/api/auth'
import { useStaffStore } from '@/stores/staff'
import { useToastStore } from '@/stores/toast'
import { parseApiError } from '@/composables/useOptimistic'

const emit = defineEmits<{ success: [user: UserOut]; cancel: [] }>()

const toast = useToastStore()
const store = useStaffStore()

const form = ref({ full_name: '', phone: '', password: '', role: 'reception' as Role })
const submitting = ref(false)
const error = ref<string | null>(null)
const showPassword = ref(false)

const ROLE_UZ: Record<Role, string> = {
  manager: 'Boshqaruvchi',
  reception: 'Qabulchi',
  technician: 'Texnik',
  cleaner: 'Tozalovchi'
}
const ROLE_HINTS: Record<Role, string> = {
  manager: 'Hamma sahifa va operatsiyalarga to‘liq kirish.',
  reception: 'Qabul/jo‘natish, mehmon profili, xona xizmati, muammo qayd etish.',
  technician: 'Texnik xizmat navbati: muammolarni qabul qilish va hal qilish.',
  cleaner: 'Tozalash navbati: xonalarni tozalashni boshlash va yakunlash.'
}

const passwordOk = computed(() => form.value.password.length >= 6)
const phoneOk = computed(() => /^\+?[1-9]\d{9,14}$/.test(form.value.phone.trim()))

async function submit() {
  error.value = null
  if (!phoneOk.value) { error.value = 'Telefon formatda bo‘lishi kerak: +998901234567.'; return }
  if (!passwordOk.value) { error.value = 'Parol kamida 6 ta belgidan iborat bo‘lsin.'; return }

  submitting.value = true
  try {
    const created = await authApi.createUser({
      phone: form.value.phone.trim(),
      password: form.value.password,
      full_name: form.value.full_name.trim() || undefined,
      role: form.value.role
    })
    store.push(created)
    toast.success(`${created.full_name || created.phone} qo‘shildi (${ROLE_UZ[created.role]})`)
    emit('success', created)
  } catch (e: unknown) {
    const err = e as { response?: { status?: number } }
    if (err.response?.status === 409) error.value = 'Bunday telefon raqamli xodim allaqachon mavjud.'
    else error.value = parseApiError(e)
  } finally { submitting.value = false }
}
</script>

<template>
  <form class="form" @submit.prevent="submit" novalidate>
    <label class="field">
      <span>To‘liq ism <span class="text-muted">(ixtiyoriy)</span></span>
      <input v-model="form.full_name" class="input" type="text" maxlength="120" autocomplete="name" />
    </label>

    <label class="field">
      <span>Telefon raqami</span>
      <input v-model="form.phone" class="input" type="tel" required placeholder="+998901234567" autocomplete="off" />
      <span v-if="form.phone && !phoneOk" class="hint hint--warn">Format: ixtiyoriy <code>+</code>, keyin 10–15 raqam.</span>
    </label>

    <label class="field">
      <span>Parol</span>
      <div class="pw">
        <input
          v-model="form.password"
          class="input"
          :type="showPassword ? 'text' : 'password'"
          required minlength="6" maxlength="128"
          autocomplete="new-password"
        />
        <button
          type="button"
          class="pw-toggle"
          @click="showPassword = !showPassword"
          :aria-label="showPassword ? 'Parolni yashirish' : 'Parolni ko‘rsatish'"
        >{{ showPassword ? 'Yashirish' : 'Ko‘rsatish' }}</button>
      </div>
      <span class="hint" :class="passwordOk ? 'hint--ok' : 'hint--warn'">
        {{ passwordOk ? '✓ Kamida 6 ta belgi.' : 'Kamida 6 ta belgi kerak.' }}
      </span>
    </label>

    <label class="field">
      <span>Rol</span>
      <select v-model="form.role" class="select" required>
        <option value="manager">Boshqaruvchi</option>
        <option value="reception">Qabulchi</option>
        <option value="technician">Texnik</option>
        <option value="cleaner">Tozalovchi</option>
      </select>
      <span class="hint">{{ ROLE_HINTS[form.role] }}</span>
    </label>

    <div v-if="error" class="error" role="alert">{{ error }}</div>

    <div class="row-foot">
      <Button variant="ghost" size="md" type="button" :disabled="submitting" @click="emit('cancel')">Bekor qilish</Button>
      <Button type="submit" variant="primary" size="md" :loading="submitting">
        {{ submitting ? 'Yaratilmoqda…' : 'Xodimni qo‘shish' }}
      </Button>
    </div>
  </form>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: 16px; }

.pw { display: flex; gap: 6px; }
.pw .input { flex: 1; }
.pw-toggle {
  padding: 0 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  font: inherit;
  font-size: var(--font-size-sm);
  color: var(--ink-600);
}
.pw-toggle:hover { background: var(--bg-subtle); }

code {
  background: var(--bg-subtle);
  padding: 1px 4px;
  border-radius: var(--radius-xs);
  font-family: var(--font-mono);
  font-size: 0.92em;
}

.error {
  padding: 11px 14px;
  background: color-mix(in srgb, var(--danger) 10%, transparent);
  color: var(--danger);
  border-radius: 10px;
  font-size: var(--font-size-sm);
}

.row-foot { display: flex; justify-content: flex-end; gap: 8px; padding-top: 4px; }
</style>
