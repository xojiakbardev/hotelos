<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { receptionApi, type GuestHistory } from '@/api/reception'
import { parseApiError } from '@/composables/useOptimistic'
import { ArrowLeft } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

const history = ref<GuestHistory | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const phone = computed(() => String(route.params.phone || ''))

function money(minor: number) { return (minor / 100).toLocaleString('uz-UZ') + " so'm" }

async function load() {
  loading.value = true
  error.value = null
  try { history.value = await receptionApi.guestHistory(phone.value) }
  catch (e: unknown) { error.value = parseApiError(e) }
  finally { loading.value = false }
}

onMounted(load)
watch(phone, load)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center gap-3">
      <Button variant="ghost" size="sm" @click="router.back()">
        <ArrowLeft class="w-4 h-4 mr-1" />
        Orqaga
      </Button>
      <h2 class="text-lg font-semibold">{{ history?.full_name || 'Mehmon tarixi' }}</h2>
    </div>

    <div v-if="error" class="rounded-md bg-destructive/10 text-destructive text-sm p-4">{{ error }}</div>
    <div v-if="loading" class="text-center py-12 text-muted-foreground">Yuklanmoqda…</div>

    <template v-else-if="history">
      <!-- Stats -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent class="p-4 text-center">
            <p class="text-2xl font-bold">{{ history.total_stays }}</p>
            <p class="text-xs text-muted-foreground">Jami tashriflar</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4 text-center">
            <p class="text-2xl font-bold">{{ history.total_nights }}</p>
            <p class="text-xs text-muted-foreground">Jami tunlar</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4 text-center">
            <p class="text-2xl font-bold text-primary">{{ money(history.total_spent_minor_units) }}</p>
            <p class="text-xs text-muted-foreground">Sarflangan</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4 text-center">
            <Badge :variant="history.repeat_visitor ? 'success' : 'secondary'">
              {{ history.repeat_visitor ? 'Doimiy mehmon' : 'Yangi mehmon' }}
            </Badge>
          </CardContent>
        </Card>
      </div>

      <!-- Stays table -->
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Xona</TableHead>
              <TableHead>Kirish</TableHead>
              <TableHead>Chiqish</TableHead>
              <TableHead class="text-right">Tunlar</TableHead>
              <TableHead class="text-right">To'lov</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="s in history.stays" :key="s.guest_id">
              <TableCell class="font-mono">#{{ s.room_number }} <span class="text-muted-foreground">/ {{ s.floor }}q</span></TableCell>
              <TableCell>{{ new Date(s.checked_in_at).toLocaleDateString('uz-UZ') }}</TableCell>
              <TableCell>{{ s.checked_out_at ? new Date(s.checked_out_at).toLocaleDateString('uz-UZ') : '—' }}</TableCell>
              <TableCell class="text-right tabular-nums">{{ s.nights }}</TableCell>
              <TableCell class="text-right font-mono tabular-nums">{{ s.total_minor_units !== null ? money(s.total_minor_units) : '—' }}</TableCell>
              <TableCell>
                <Badge :variant="s.checked_out_at ? 'success' : 'default'">
                  {{ s.checked_out_at ? 'Yakunlangan' : 'Mehmonxonada' }}
                </Badge>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Card>
    </template>
  </div>
</template>
