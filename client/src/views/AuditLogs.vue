<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { api } from '@/api/client'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { Skeleton } from '@/components/ui/skeleton'

interface AuditLog {
  id: string
  actor_user_id: string | null
  actor_role: string | null
  actor_phone: string | null
  actor_name: string | null
  action: string
  entity_type: string | null
  entity_id: string | null
  metadata_json: Record<string, unknown>
  created_at: string
}

const logs = ref<AuditLog[]>([])
const total = ref(0)
const loading = ref(true)
const offset = ref(0)
const limit = 50

const ACTION_UZ: Record<string, string> = {
  USER_LOGIN: 'Kirish',
  PASSWORD_CHANGED: "Parol o'zgartirildi",
  USER_CREATED: 'Foydalanuvchi yaratildi',
  GUEST_CHECKED_IN: 'Mehmon qabul qilindi',
  GUEST_CHECKED_OUT: "Mehmon jo'natildi",
  ORDER_PLACED: 'Buyurtma berildi',
  CLEANING_TASK_COMPLETED: 'Tozalash yakunlandi',
  MAINTENANCE_TICKET_CREATED: 'Muammo yaratildi',
  MAINTENANCE_TICKET_RESOLVED: 'Muammo hal qilindi',
}

const ROLE_UZ: Record<string, string> = {
  manager: 'Boshqaruvchi',
  reception: 'Qabulchi',
  technician: 'Texnik',
  cleaner: 'Tozalovchi',
  guest: 'Mehmon',
}

async function load() {
  loading.value = true
  try {
    const res = await api.get('/auth/audit-logs', { params: { offset: offset.value, limit } })
    logs.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

function nextPage() { offset.value += limit; load() }
function prevPage() { offset.value = Math.max(0, offset.value - limit); load() }

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <div v-if="loading" class="space-y-3">
      <Card>
        <div class="p-4 space-y-4">
          <div v-for="i in 8" :key="i" class="flex items-center gap-6">
            <Skeleton class="h-4 w-36" />
            <Skeleton class="h-4 w-32" />
            <Skeleton class="h-5 w-20 rounded-full" />
            <Skeleton class="h-4 w-28" />
          </div>
        </div>
      </Card>
    </div>
    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Vaqt</TableHead>
            <TableHead>Harakat</TableHead>
            <TableHead>Foydalanuvchi</TableHead>
            <TableHead>Rol</TableHead>
            <TableHead>Ob'ekt</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="l in logs" :key="l.id">
            <TableCell class="font-mono text-xs text-muted-foreground">{{ new Date(l.created_at).toLocaleString('uz-UZ') }}</TableCell>
            <TableCell class="font-medium">{{ ACTION_UZ[l.action] || l.action }}</TableCell>
            <TableCell>
              <div v-if="l.actor_name || l.actor_phone">
                <p class="text-sm font-medium">{{ l.actor_name || '—' }}</p>
                <p class="text-xs text-muted-foreground font-mono">{{ l.actor_phone }}</p>
              </div>
              <span v-else class="text-muted-foreground">—</span>
            </TableCell>
            <TableCell>
              <Badge variant="secondary">{{ ROLE_UZ[l.actor_role || ''] || l.actor_role || '—' }}</Badge>
            </TableCell>
            <TableCell class="text-muted-foreground text-xs">{{ l.entity_type ? `${l.entity_type}/${l.entity_id?.slice(0, 8)}` : '—' }}</TableCell>
          </TableRow>
        </TableBody>
      </Table>
      <!-- Pagination -->
      <div class="flex items-center justify-center gap-4 p-4 border-t">
        <Button variant="outline" size="sm" :disabled="offset === 0" @click="prevPage">
          <ChevronLeft class="w-4 h-4 mr-1" />
          Oldingi
        </Button>
        <span class="text-sm text-muted-foreground tabular-nums">
          {{ offset + 1 }}–{{ Math.min(offset + limit, total) }} / {{ total }}
        </span>
        <Button variant="outline" size="sm" :disabled="offset + limit >= total" @click="nextPage">
          Keyingi
          <ChevronRight class="w-4 h-4 ml-1" />
        </Button>
      </div>
    </Card>
  </div>
</template>
