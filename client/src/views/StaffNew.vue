<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { authApi, type Role, type UserOut } from '@/api/auth'
import { useStaffStore } from '@/stores/staff'
import { useToastStore } from '@/stores/toast'
import { parseApiError } from '@/composables/useOptimistic'
import { Loader2, Eye, EyeOff } from 'lucide-vue-next'

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
  cleaner: 'Tozalovchi',
  guest: 'Mehmon'
}
const ROLE_HINTS: Record<string, string> = {
  manager: "Hamma sahifa va operatsiyalarga to'liq kirish.",
  reception: "Qabul/jo'natish, mehmon profili, xona xizmati.",
  technician: 'Texnik xizmat navbati: muammolarni qabul qilish va hal qilish.',
  cleaner: 'Tozalash navbati: xonalarni tozalashni boshlash va yakunlash.',
}

const passwordOk = computed(() => form.value.password.length >= 6)
const phoneOk = computed(() => /^\+?[1-9]\d{9,14}$/.test(form.value.phone.trim()))

async function submit() {
  error.value = null
  if (!phoneOk.value) { error.value = "Telefon formatda bo'lishi kerak: +998901234567."; return }
  if (!passwordOk.value) { error.value = "Parol kamida 6 ta belgidan iborat bo'lsin."; return }

  submitting.value = true
  try {
    const created = await authApi.createUser({
      phone: form.value.phone.trim(),
      password: form.value.password,
      full_name: form.value.full_name.trim() || undefined,
      role: form.value.role
    })
    store.push(created)
    toast.success(`${created.full_name || created.phone} qo'shildi (${ROLE_UZ[created.role]})`)
    emit('success', created)
  } catch (e: unknown) {
    const err = e as { response?: { status?: number } }
    if (err.response?.status === 409) error.value = 'Bunday telefon raqamli xodim allaqachon mavjud.'
    else error.value = parseApiError(e)
  } finally { submitting.value = false }
}
</script>

<template>
  <form @submit.prevent="submit" class="space-y-4" novalidate>
    <div class="space-y-2">
      <Label>To'liq ism (ixtiyoriy)</Label>
      <Input v-model="form.full_name" autocomplete="name" />
    </div>

    <div class="space-y-2">
      <Label>Telefon raqami</Label>
      <Input v-model="form.phone" type="tel" placeholder="+998901234567" required autocomplete="off" />
      <p v-if="form.phone && !phoneOk" class="text-xs text-amber-600">Format: +998XXXXXXXXX</p>
    </div>

    <div class="space-y-2">
      <Label>Parol</Label>
      <div class="flex gap-2">
        <Input
          v-model="form.password"
          :type="showPassword ? 'text' : 'password'"
          required
          autocomplete="new-password"
          class="flex-1"
        />
        <Button variant="outline" size="icon" type="button" @click="showPassword = !showPassword">
          <component :is="showPassword ? EyeOff : Eye" class="w-4 h-4" />
        </Button>
      </div>
      <p :class="passwordOk ? 'text-xs text-green-600' : 'text-xs text-amber-600'">
        {{ passwordOk ? '✓ Kamida 6 ta belgi.' : 'Kamida 6 ta belgi kerak.' }}
      </p>
    </div>

    <div class="space-y-2">
      <Label>Rol</Label>
      <Select v-model="form.role">
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="manager">Boshqaruvchi</SelectItem>
          <SelectItem value="reception">Qabulchi</SelectItem>
          <SelectItem value="technician">Texnik</SelectItem>
          <SelectItem value="cleaner">Tozalovchi</SelectItem>
        </SelectContent>
      </Select>
      <p class="text-xs text-muted-foreground">{{ ROLE_HINTS[form.role] }}</p>
    </div>

    <div v-if="error" class="rounded-md bg-destructive/10 text-destructive text-sm p-3" role="alert">{{ error }}</div>

    <div class="flex justify-end gap-2 pt-2">
      <Button variant="outline" type="button" :disabled="submitting" @click="emit('cancel')">Bekor</Button>
      <Button type="submit" :disabled="submitting">
        <Loader2 v-if="submitting" class="w-4 h-4 mr-2 animate-spin" />
        Xodimni qo'shish
      </Button>
    </div>
  </form>
</template>
