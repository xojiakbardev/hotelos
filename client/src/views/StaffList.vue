<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import Button from '@/components/Button.vue'
import StatCard from '@/components/StatCard.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import Modal from '@/components/Modal.vue'
import StaffNew from './StaffNew.vue'
import type { Role } from '@/api/auth'
import { useStaffStore } from '@/stores/staff'
import { ROLE_UZ } from '@/lib/labels'

const store = useStaffStore()

const filterRole = ref<'all' | Role>('all')
const addOpen = ref(false)

const visible = computed(() => {
  if (filterRole.value === 'all') return store.users
  return store.users.filter((u) => u.role === filterRole.value)
})

const ROLE_TONE: Record<Role, string> = {
  manager: 'occupied',
  reception: 'cleaning',
  technician: 'maintenance',
  cleaner: 'clean'
}

onMounted(() => store.load())
</script>

<template>
  <div class="page">
    <PageHeader title="Xodimlar">
      <template #actions>
        <Button variant="primary" size="md" @click="addOpen = true">Xodim qo‘shish</Button>
      </template>
    </PageHeader>

    <section class="stats">
      <StatCard label="Jami xodim" :value="store.users.length" hint="Faol akkauntlar" />
      <StatCard label="Boshqaruvchi" :value="store.counts.manager" hint="To‘liq kirish" tone="primary" />
      <StatCard label="Qabulchi" :value="store.counts.reception" hint="Mehmon va buyurtma" tone="primary" />
      <StatCard label="Texnik" :value="store.counts.technician" hint="Muammolarni hal qiladi" tone="warn" />
      <StatCard label="Tozalovchi" :value="store.counts.cleaner" hint="Tozalash navbati" tone="success" />
    </section>

    <section class="filters card-paper">
      <label class="field inline">
        <span>Rol</span>
        <select v-model="filterRole" class="select">
          <option value="all">Hammasi</option>
          <option value="manager">Boshqaruvchi</option>
          <option value="reception">Qabulchi</option>
          <option value="technician">Texnik</option>
          <option value="cleaner">Tozalovchi</option>
        </select>
      </label>
    </section>

    <section v-if="store.error" class="error">{{ store.error }}</section>
    <section v-if="store.loading && !store.users.length" class="empty card-paper">Yuklanmoqda…</section>
    <section v-else-if="!visible.length" class="empty card-paper">Filtr bo‘yicha xodim topilmadi.</section>

    <article v-else class="card-paper table-wrap">
      <table class="data">
        <thead>
          <tr>
            <th>Xodim</th>
            <th>Telefon</th>
            <th>Rol</th>
            <th>Holati</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in visible" :key="u.id">
            <td>
              <div class="cell-name">
                <span class="avatar">{{ (u.full_name || u.phone || '?').slice(0, 1).toUpperCase() }}</span>
                <span class="name">{{ u.full_name || '—' }}</span>
              </div>
            </td>
            <td class="mono text-muted">{{ u.phone }}</td>
            <td><StatusBadge :tone="ROLE_TONE[u.role]" :label="ROLE_UZ[u.role]" /></td>
            <td>
              <StatusBadge
                :tone="u.is_active ? 'clean' : 'low'"
                :label="u.is_active ? 'Faol' : 'O‘chirilgan'"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </article>

    <Modal :open="addOpen" title="Xodim qo‘shish" size="md" @close="addOpen = false">
      <StaffNew @cancel="addOpen = false" @success="addOpen = false" />
    </Modal>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
}

.filters { display: flex; gap: 16px; padding: 14px 18px; }
.field.inline { flex-direction: row; align-items: center; gap: 10px; min-width: 280px; }
.field.inline > span:first-child {
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted-fg);
  font-weight: 600;
  flex-shrink: 0;
}
.field.inline .select { min-width: 200px; }

.error {
  padding: 14px;
  background: color-mix(in srgb, var(--danger) 10%, transparent);
  color: var(--danger);
  border-radius: var(--radius-md);
}
.empty { padding: 48px; text-align: center; color: var(--muted-fg); }

.table-wrap { padding: 0; overflow: hidden; }

.data {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}
.data th, .data td {
  padding: 12px 18px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}
.data thead th {
  background: var(--bg-subtle);
  font-weight: 600;
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted-fg);
}
.data tbody tr:last-child td { border-bottom: none; }
.data tbody tr:hover { background: var(--bg-subtle); }
.mono { font-family: var(--font-mono); }

.cell-name { display: flex; align-items: center; gap: 10px; }
.avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: var(--primary-soft-2);
  color: var(--primary-strong);
  display: grid;
  place-items: center;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--font-size-sm);
  flex-shrink: 0;
}
.name { font-weight: 500; color: var(--ink-900); }
</style>
