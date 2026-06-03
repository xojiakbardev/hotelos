<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import Button from '@/components/Button.vue'
import Modal from '@/components/Modal.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { menuApi, type MenuItem } from '@/api/menu'
import { useToastStore } from '@/stores/toast'
import { parseApiError } from '@/composables/useOptimistic'

const items = ref<MenuItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const editor = ref<MenuItem | 'new' | null>(null)
const toDelete = ref<MenuItem | null>(null)
const saving = ref(false)
const toast = useToastStore()

const draft = ref({
  name: '',
  category: 'mains',
  price_dollars: 0,
  prep_minutes: 10,
  is_available: true
})

const availableCount = computed(() => items.value.filter((i) => i.is_available).length)
const unavailableCount = computed(() => items.value.length - availableCount.value)

function money(minor: number) { return `$${(minor / 100).toFixed(2)}` }

async function load() {
  loading.value = true
  try { items.value = await menuApi.list(false) }
  catch (e: unknown) { error.value = parseApiError(e) }
  finally { loading.value = false }
}

onMounted(load)

function openEditor(item: MenuItem | 'new') {
  editor.value = item
  if (item === 'new') {
    draft.value = { name: '', category: 'mains', price_dollars: 0, prep_minutes: 10, is_available: true }
  } else {
    draft.value = {
      name: item.name,
      category: item.category,
      price_dollars: item.price_minor_units / 100,
      prep_minutes: item.prep_minutes,
      is_available: item.is_available
    }
  }
}

async function saveDraft() {
  if (!editor.value) return
  saving.value = true
  try {
    const payload = {
      name: draft.value.name.trim(),
      category: draft.value.category.trim() || 'other',
      price_minor_units: Math.round(draft.value.price_dollars * 100),
      prep_minutes: draft.value.prep_minutes,
      is_available: draft.value.is_available
    }
    if (editor.value === 'new') {
      const created = await menuApi.create(payload)
      items.value = [created, ...items.value]
      toast.success(`“${created.name}” menyuga qo‘shildi`)
    } else {
      const updated = await menuApi.update(editor.value.id, payload)
      items.value = items.value.map((i) => (i.id === updated.id ? updated : i))
      toast.success(`“${updated.name}” yangilandi`)
    }
    editor.value = null
  } catch (e: unknown) {
    toast.error(parseApiError(e))
  } finally {
    saving.value = false
  }
}

async function toggleAvailability(item: MenuItem) {
  const target = !item.is_available
  const before = item.is_available
  item.is_available = target
  try {
    const updated = await menuApi.setAvailability(item.id, target)
    Object.assign(item, updated)
  } catch (e) {
    item.is_available = before
    toast.error(parseApiError(e))
  }
}

async function confirmDelete() {
  if (!toDelete.value) return
  const id = toDelete.value.id
  try {
    await menuApi.remove(id)
    items.value = items.value.filter((i) => i.id !== id)
    toast.info('Mahsulot menyudan o‘chirildi')
  } catch (e) {
    toast.error(parseApiError(e))
  } finally {
    toDelete.value = null
  }
}
</script>

<template>
  <div class="page">
    <PageHeader title="Xona xizmati menyusi">
      <template #actions>
        <Button variant="primary" size="md" @click="openEditor('new')">+ Mahsulot qo‘shish</Button>
      </template>
    </PageHeader>

    <section class="stats">
      <div class="stat-pill">
        <span class="dot dot--ok"></span>
        Mavjud: <strong>{{ availableCount }}</strong>
      </div>
      <div class="stat-pill">
        <span class="dot dot--off"></span>
        Mavjud emas: <strong>{{ unavailableCount }}</strong>
      </div>
    </section>

    <section v-if="error" class="error">{{ error }}</section>
    <section v-if="loading" class="empty card-paper">Yuklanmoqda…</section>
    <section v-else-if="!items.length" class="empty card-paper">
      Menyu hozircha bo‘sh. “Mahsulot qo‘shish” tugmasini bosing.
    </section>

    <article v-else class="card-paper table-wrap">
      <table class="data">
        <thead>
          <tr>
            <th>Nomi</th>
            <th>Kategoriya</th>
            <th class="num">Narxi</th>
            <th class="num">Tayyorlash</th>
            <th>Status</th>
            <th class="num">Harakat</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="i in items" :key="i.id" :class="{ disabled: !i.is_available }">
            <td>{{ i.name }}</td>
            <td class="text-muted">{{ i.category }}</td>
            <td class="num mono tabular">{{ money(i.price_minor_units) }}</td>
            <td class="num mono tabular">{{ i.prep_minutes }} daq</td>
            <td>
              <button type="button" class="chip-btn" :class="{ 'chip-btn--off': !i.is_available }" @click="toggleAvailability(i)">
                {{ i.is_available ? 'Mavjud' : 'O‘chirilgan' }}
              </button>
            </td>
            <td class="num">
              <Button variant="ghost" size="sm" @click="openEditor(i)">Tahrirlash</Button>
              <Button variant="ghost" size="sm" @click="toDelete = i">O‘chirish</Button>
            </td>
          </tr>
        </tbody>
      </table>
    </article>

    <Modal :open="editor !== null" :title="editor === 'new' ? 'Yangi mahsulot' : 'Mahsulotni tahrirlash'" size="md" @close="editor = null">
      <form class="form" @submit.prevent="saveDraft">
        <label class="field"><span>Nomi</span><input v-model="draft.name" class="input" type="text" required maxlength="64" /></label>
        <label class="field"><span>Kategoriya</span>
          <select v-model="draft.category" class="select">
            <option value="drinks">drinks</option>
            <option value="mains">mains</option>
            <option value="desserts">desserts</option>
            <option value="other">other</option>
          </select>
        </label>
        <div class="row">
          <label class="field"><span>Narxi ($)</span><input v-model.number="draft.price_dollars" class="input" type="number" min="0.01" step="0.50" required /></label>
          <label class="field"><span>Tayyorlash (daq)</span><input v-model.number="draft.prep_minutes" class="input" type="number" min="1" max="240" required /></label>
        </div>
        <label class="field check"><input v-model="draft.is_available" type="checkbox" /> <span>Hozirda mavjud</span></label>
        <div class="row-foot">
          <Button variant="ghost" type="button" :disabled="saving" @click="editor = null">Bekor qilish</Button>
          <Button type="submit" variant="primary" :loading="saving">Saqlash</Button>
        </div>
      </form>
    </Modal>

    <ConfirmDialog
      :open="toDelete !== null"
      :title="toDelete ? `“${toDelete.name}” o‘chirilsinmi?` : ''"
      message="O‘chirilgan mahsulot avtomatik ravishda menyudan yo‘qoladi."
      confirm-label="O‘chirish"
      cancel-label="Bekor qilish"
      tone="destructive"
      @cancel="toDelete = null"
      @confirm="confirmDelete"
    />
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }

.stats { display: flex; gap: 12px; }
.stat-pill { display: flex; align-items: center; gap: 8px; padding: 8px 14px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-full); font-size: var(--font-size-sm); }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot--ok { background: var(--success, #059669); }
.dot--off { background: var(--muted-fg); }

.error { padding: 14px; background: color-mix(in srgb, var(--danger) 10%, transparent); color: var(--danger); border-radius: var(--radius-md); }
.empty { padding: 48px; text-align: center; color: var(--muted-fg); }
.table-wrap { padding: 0; overflow: hidden; }
.data { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.data th, .data td { padding: 12px 18px; text-align: left; border-bottom: 1px solid var(--border); }
.data thead th { background: var(--bg-subtle); font-weight: 600; font-size: var(--font-size-xs); text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted-fg); }
.data tbody tr:last-child td { border-bottom: none; }
.data .num { text-align: right; }
.mono { font-family: var(--font-mono); }
.data tr.disabled td { color: var(--muted-fg); }

.chip-btn { padding: 4px 10px; border-radius: var(--radius-full); border: 1px solid var(--border); background: var(--bg-subtle); cursor: pointer; font-size: var(--font-size-xs); font-weight: 500; }
.chip-btn--off { color: var(--muted-fg); }

.form { display: flex; flex-direction: column; gap: 12px; }
.form .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.form .check { flex-direction: row; align-items: center; gap: 8px; }
.row-foot { display: flex; justify-content: flex-end; gap: 8px; padding-top: 4px; }
</style>
