<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { receptionApi, type Room } from '@/api/reception'
import { maintenanceApi, type Issue, type Urgency } from '@/api/maintenance'
import { useToastStore } from '@/stores/toast'
import { parseApiError } from '@/composables/useOptimistic'
import { URGENCY_UZ } from '@/lib/labels'
import { Loader2 } from 'lucide-vue-next'

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
  <form @submit.prevent="submit" class="space-y-4" novalidate>
    <div class="space-y-2">
      <Label>Xona</Label>
      <Select v-model="form.room_id" :disabled="loadingRooms">
        <SelectTrigger>
          <SelectValue :placeholder="loadingRooms ? 'Yuklanmoqda…' : 'Xonani tanlang'" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem v-for="r in rooms" :key="r.id" :value="r.id">
            #{{ r.room_number }} · {{ r.floor }}-qavat · {{ r.room_type }}
          </SelectItem>
        </SelectContent>
      </Select>
    </div>

    <div class="space-y-2">
      <Label>Shoshilinchlik darajasi</Label>
      <Select v-model="form.urgency">
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="critical">Kritik — darhol tuzating</SelectItem>
          <SelectItem value="high">Yuqori — bugun</SelectItem>
          <SelectItem value="normal">O'rta — 24 soat ichida</SelectItem>
          <SelectItem value="low">Past — shoshilinch emas</SelectItem>
        </SelectContent>
      </Select>
    </div>

    <div class="space-y-2">
      <Label>Tavsif</Label>
      <Textarea
        v-model="form.description"
        required
        placeholder="masalan, hammomda quvur yorilgan, polda suv"
        class="min-h-[100px]"
      />
    </div>

    <div v-if="error" class="rounded-md bg-destructive/10 text-destructive text-sm p-3" role="alert">{{ error }}</div>

    <div class="flex justify-end gap-2 pt-2">
      <Button variant="outline" type="button" :disabled="submitting" @click="emit('cancel')">Bekor</Button>
      <Button type="submit" :disabled="submitting || loadingRooms">
        <Loader2 v-if="submitting" class="w-4 h-4 mr-2 animate-spin" />
        Qayd etish
      </Button>
    </div>
  </form>
</template>
