<script setup lang="ts">
/**
 * Embeddable "report issue" form. Mounted in a Modal from MaintenanceQueue.
 */
import { computed, onMounted, ref } from 'vue'
import Button from '@/components/Button.vue'
import { receptionApi, type Room } from '@/api/reception'
import { maintenanceApi, type Issue, type Urgency } from '@/api/maintenance'
import { useToastStore } from '@/stores/toast'
import { parseApiError } from '@/composables/useOptimistic'
import { URGENCY_UZ } from '@/lib/labels'

const emit = defineEmits<{ success: [issue: Issue]; cancel: [] }>()
const toast = useToastStore()

const rooms = ref<Room[]>([])
const loadingRooms = ref(true)

const form = ref({ room_id: '', urgency: 'normal' as Urgency, description: '' })
const submitting = ref(false)
const error = ref<string | null>(null)

const selectedRoom = computed(() => rooms.value.find((r) => r.id === form.value.room_id) ?? null)

onMounted(async () => {
  try {
    const res = await receptionApi.listRooms()
    rooms.value = res.rooms.sort((a, b) => a.room_number - b.room_number)
  } catch (e: unknown) { error.value = parseApiError(e) }
  finally { loadingRooms.value = false }
})

const TYPE_UZ: Record<string, string> = {
  single: 'bir kishilik', double: 'ikki kishilik', suite: 'lyuks', accessible: 'nogironlar uchun'
}
const CLEAN_UZ: Record<string, string> = {
  clean: 'toza', dirty: 'iflos', cleaning: 'tozalanmoqda', maintenance: 'texnik xizmatda'
}

async function submit() {
  error.value = null
  if (!selectedRoom.value) { error.value = 'Xonani tanlang.'; return }
  submitting.value = true
  try {
    const issue = await maintenanceApi.report({
      room_id: selectedRoom.value.id,
      room_number: selectedRoom.value.room_number,
      floor: selectedRoom.value.floor,
      urgency: form.value.urgency,
      description: form.value.description.trim()
    })
    toast.success(`#${issue.room_number}-xonada ${(URGENCY_UZ[issue.urgency] ?? issue.urgency).toLowerCase()} darajadagi muammo qayd etildi`)
    emit('success', issue)
  } catch (e: unknown) { error.value = parseApiError(e) }
  finally { submitting.value = false }
}
</script>

<template>
  <form class="form" @submit.prevent="submit" novalidate>
    <label class="field">
      <span>Xona</span>
      <select v-model="form.room_id" class="select" required :disabled="loadingRooms">
        <option value="" disabled>{{ loadingRooms ? 'Xonalar yuklanmoqda…' : 'Xonani tanlang' }}</option>
        <option v-for="r in rooms" :key="r.id" :value="r.id">
          #{{ r.room_number }} · {{ r.floor }}-qavat · {{ TYPE_UZ[r.room_type] }} · {{ CLEAN_UZ[r.cleanliness_status] }}
        </option>
      </select>
    </label>

    <label class="field">
      <span>Shoshilinchlik darajasi</span>
      <select v-model="form.urgency" class="select" required>
        <option value="critical">Kritik — mehmonlarga xavfli, darhol tuzating</option>
        <option value="high">Yuqori — bugun mehmonga ta’sir qiladi</option>
        <option value="normal">O‘rta — 24 soat ichida tuzating</option>
        <option value="low">Past — kosmetik, shoshilinch emas</option>
      </select>
    </label>

    <label class="field">
      <span>Tavsif</span>
      <textarea
        v-model="form.description"
        class="textarea"
        required
        minlength="3"
        maxlength="500"
        rows="4"
        placeholder="masalan, hammomda quvur yorilgan, polda suv"
      />
    </label>

    <div v-if="error" class="error" role="alert">{{ error }}</div>

    <div class="row-foot">
      <Button variant="ghost" size="md" type="button" :disabled="submitting" @click="emit('cancel')">Bekor qilish</Button>
      <Button type="submit" variant="primary" size="md" :loading="submitting || loadingRooms">
        {{ submitting ? 'Yuborilmoqda…' : 'Qayd etish' }}
      </Button>
    </div>
  </form>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: 16px; }

.error {
  padding: 11px 14px;
  background: color-mix(in srgb, var(--danger) 10%, transparent);
  color: var(--danger);
  border-radius: 10px;
  font-size: var(--font-size-sm);
}

.row-foot { display: flex; justify-content: flex-end; gap: 8px; padding-top: 4px; }
</style>
