<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator } from '@/components/ui/dropdown-menu'
import StaffNew from './StaffNew.vue'
import { authApi, type Role, type UserOut } from '@/api/auth'
import { useStaffStore } from '@/stores/staff'
import { useToastStore } from '@/stores/toast'
import { ROLE_UZ } from '@/lib/labels'
import { Plus, Search, Trash2, MoreVertical, Pencil, Loader2, Eye, EyeOff } from 'lucide-vue-next'
import { Skeleton } from '@/components/ui/skeleton'

const store = useStaffStore()
const toast = useToastStore()

const filterRole = ref('all')
const searchQuery = ref('')
const addOpen = ref(false)
const deleteDialogOpen = ref(false)
const toDelete = ref<UserOut | null>(null)

// Edit state
const editOpen = ref(false)
const editUser = ref<UserOut | null>(null)
const editSaving = ref(false)
const editDraft = ref({
  full_name: '',
  role: 'reception' as Role,
  password: '',
  is_active: true,
})
const showEditPassword = ref(false)

const visible = computed(() => {
  let list = store.users
  if (filterRole.value !== 'all') {
    list = list.filter((u) => u.role === filterRole.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(u =>
      (u.full_name || '').toLowerCase().includes(q) ||
      u.phone.includes(q)
    )
  }
  return list
})

function roleVariant(role: Role): 'default' | 'secondary' | 'success' | 'warning' {
  if (role === 'manager') return 'default'
  if (role === 'reception') return 'secondary'
  if (role === 'technician') return 'warning'
  return 'success'
}

onMounted(() => store.load())

function openEdit(u: UserOut) {
  editUser.value = u
  editDraft.value = {
    full_name: u.full_name || '',
    role: u.role,
    password: '',
    is_active: u.is_active,
  }
  showEditPassword.value = false
  editOpen.value = true
}

async function saveEdit() {
  if (!editUser.value) return
  editSaving.value = true
  try {
    const payload: Record<string, any> = {}
    if (editDraft.value.full_name !== (editUser.value.full_name || '')) {
      payload.full_name = editDraft.value.full_name || null
    }
    if (editDraft.value.role !== editUser.value.role) {
      payload.role = editDraft.value.role
    }
    if (editDraft.value.password.length >= 6) {
      payload.password = editDraft.value.password
    }
    if (editDraft.value.is_active !== editUser.value.is_active) {
      payload.is_active = editDraft.value.is_active
    }

    if (Object.keys(payload).length === 0) {
      editOpen.value = false
      return
    }

    await authApi.updateUser(editUser.value.id, payload)
    toast.success('Xodim yangilandi')
    editOpen.value = false
    store.load()
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || 'Yangilashda xatolik')
  } finally {
    editSaving.value = false
  }
}

function askDelete(u: UserOut) {
  toDelete.value = u
  deleteDialogOpen.value = true
}

async function doDelete() {
  if (!toDelete.value) return
  try {
    await authApi.deleteUser(toDelete.value.id)
    toast.info(`${toDelete.value.full_name || toDelete.value.phone} o'chirildi`)
    store.load()
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || "O'chirishda xatolik")
  } finally {
    toDelete.value = null
    deleteDialogOpen.value = false
  }
}

function onStaffAdded() {
  addOpen.value = false
  store.load()
}
</script>

<template>
  <div class="space-y-6">
    <!-- Filters -->
    <Card>
      <CardContent class="p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div class="flex gap-3 items-center">
          <div class="relative">
            <Search class="absolute left-2.5 top-2.5 w-4 h-4 text-muted-foreground" />
            <Input v-model="searchQuery" placeholder="Ism yoki telefon..." class="pl-9 w-[200px]" />
          </div>
          <Select v-model="filterRole">
            <SelectTrigger class="w-[160px]">
              <SelectValue placeholder="Rol" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Barcha rollar</SelectItem>
              <SelectItem value="manager">Boshqaruvchi</SelectItem>
              <SelectItem value="reception">Qabulchi</SelectItem>
              <SelectItem value="technician">Texnik</SelectItem>
              <SelectItem value="cleaner">Tozalovchi</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button size="sm" @click="addOpen = true">
          <Plus class="w-4 h-4 mr-1" />
          Xodim qo'shish
        </Button>
      </CardContent>
    </Card>

    <!-- States -->
    <div v-if="store.error" class="rounded-md bg-destructive/10 text-destructive text-sm p-4">{{ store.error }}</div>
    <div v-if="store.loading && !store.users.length" class="space-y-3">
      <Card>
        <div class="p-4 space-y-4">
          <div v-for="i in 4" :key="i" class="flex items-center gap-4">
            <Skeleton class="h-8 w-8 rounded-full" />
            <Skeleton class="h-4 w-32" />
            <Skeleton class="h-4 w-28" />
            <Skeleton class="h-5 w-20 rounded-full" />
            <Skeleton class="h-4 w-12 ml-auto" />
          </div>
        </div>
      </Card>
    </div>
    <div v-else-if="!visible.length" class="text-center py-12 text-muted-foreground">Xodim topilmadi.</div>

    <!-- Table -->
    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Xodim</TableHead>
            <TableHead>Telefon</TableHead>
            <TableHead>Rol</TableHead>
            <TableHead>Holat</TableHead>
            <TableHead class="text-right">Harakat</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="u in visible" :key="u.id">
            <TableCell>
              <div class="flex items-center gap-2.5">
                <Avatar class="h-8 w-8">
                  <AvatarFallback class="text-xs bg-primary/10 text-primary">
                    {{ (u.full_name || u.phone || '?').slice(0, 1).toUpperCase() }}
                  </AvatarFallback>
                </Avatar>
                <span class="font-medium">{{ u.full_name || '—' }}</span>
              </div>
            </TableCell>
            <TableCell class="text-muted-foreground font-mono text-xs">{{ u.phone }}</TableCell>
            <TableCell><Badge :variant="roleVariant(u.role)">{{ ROLE_UZ[u.role] || u.role }}</Badge></TableCell>
            <TableCell>
              <span :class="u.is_active ? 'text-green-600 font-medium text-xs' : 'text-muted-foreground text-xs'">
                {{ u.is_active ? 'Faol' : "O'chiq" }}
              </span>
            </TableCell>
            <TableCell class="text-right">
              <DropdownMenu>
                <DropdownMenuTrigger as-child>
                  <Button variant="ghost" size="icon-sm">
                    <MoreVertical class="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem @click="openEdit(u)">
                    <Pencil class="w-4 h-4 mr-2" />
                    Tahrirlash
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem class="text-destructive focus:text-destructive" @click="askDelete(u)">
                    <Trash2 class="w-4 h-4 mr-2" />
                    O'chirish
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>

    <!-- Add Staff Dialog -->
    <Dialog :open="addOpen" @update:open="addOpen = $event">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Xodim qo'shish</DialogTitle>
        </DialogHeader>
        <StaffNew @cancel="addOpen = false" @success="onStaffAdded" />
      </DialogContent>
    </Dialog>

    <!-- Edit Staff Dialog -->
    <Dialog :open="editOpen" @update:open="editOpen = $event">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Xodimni tahrirlash</DialogTitle>
        </DialogHeader>
        <form v-if="editUser" @submit.prevent="saveEdit" class="space-y-4">
          <div class="space-y-2">
            <Label>Telefon</Label>
            <Input :model-value="editUser.phone" disabled class="opacity-60" />
          </div>
          <div class="space-y-2">
            <Label>To'liq ism</Label>
            <Input v-model="editDraft.full_name" />
          </div>
          <div class="space-y-2">
            <Label>Rol</Label>
            <Select v-model="editDraft.role">
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
          </div>
          <div class="space-y-2">
            <Label>Yangi parol (bo'sh qoldirsa o'zgarmaydi)</Label>
            <div class="flex gap-2">
              <Input
                v-model="editDraft.password"
                :type="showEditPassword ? 'text' : 'password'"
                placeholder="••••••••"
                class="flex-1"
              />
              <Button variant="outline" size="icon" type="button" @click="showEditPassword = !showEditPassword">
                <component :is="showEditPassword ? EyeOff : Eye" class="w-4 h-4" />
              </Button>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <input id="edit-active" v-model="editDraft.is_active" type="checkbox" class="rounded border-input" />
            <Label for="edit-active">Faol</Label>
          </div>
          <DialogFooter>
            <Button variant="outline" type="button" :disabled="editSaving" @click="editOpen = false">Bekor</Button>
            <Button type="submit" :disabled="editSaving">
              <Loader2 v-if="editSaving" class="w-4 h-4 mr-2 animate-spin" />
              Saqlash
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>

    <!-- Delete confirmation -->
    <Dialog :open="deleteDialogOpen" @update:open="deleteDialogOpen = $event">
      <DialogContent class="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>{{ toDelete ? `${toDelete.full_name || toDelete.phone} ni o'chirish?` : '' }}</DialogTitle>
          <p class="text-sm text-muted-foreground">Xodim o'chirilganda tizimga kira olmaydi.</p>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" @click="deleteDialogOpen = false; toDelete = null">Bekor</Button>
          <Button variant="destructive" @click="doDelete">O'chirish</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
