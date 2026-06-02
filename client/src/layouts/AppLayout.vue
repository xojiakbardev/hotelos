<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useWsStore } from '@/stores/ws'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const ws = useWsStore()

interface NavItem { to: string; label: string; roles: string[] }

const NAV: NavItem[] = [
  { to: '/',              label: 'Boshqaruv paneli', roles: ['manager', 'reception', 'technician', 'cleaner'] },
  { to: '/rooms',         label: 'Xonalar',          roles: ['manager', 'reception', 'cleaner', 'technician'] },
  { to: '/guests',        label: 'Mehmonlar',        roles: ['manager', 'reception'] },
  { to: '/orders',        label: 'Xona xizmati',     roles: ['manager', 'reception'] },
  { to: '/housekeeping',  label: 'Tozalash',         roles: ['manager', 'cleaner'] },
  { to: '/maintenance',   label: 'Texnik xizmat',    roles: ['manager', 'technician', 'reception'] },
  { to: '/staff',         label: 'Xodimlar',         roles: ['manager'] }
]

const ROLE_UZ: Record<string, string> = {
  manager: 'Boshqaruvchi',
  reception: 'Qabulchi',
  technician: 'Texnik',
  cleaner: 'Tozalovchi'
}

const items = computed(() =>
  auth.role ? NAV.filter((i) => i.roles.includes(auth.role!)) : []
)

const currentTitle = computed(() => {
  const found = NAV.find((n) => n.to === route.path)
  if (found) return found.label
  if (route.path.startsWith('/rooms/check-in'))    return 'Mehmonni qabul qilish'
  if (route.path.startsWith('/orders/new'))        return 'Yangi buyurtma'
  if (route.path.startsWith('/maintenance/report')) return 'Muammo qayd etish'
  if (route.path.startsWith('/staff/new'))         return 'Xodim qo‘shish'
  return (route.meta.title as string) || ''
})

function logout() {
  ws.disconnect()
  auth.logout()
  router.push({ name: 'login' })
}

function isActive(to: string) {
  if (to === '/') return route.path === '/'
  return route.path === to || route.path.startsWith(to + '/')
}
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark">H</span>
        <span class="brand-name">HotelOS</span>
      </div>

      <nav class="nav">
        <RouterLink
          v-for="i in items"
          :key="i.to"
          :to="i.to"
          :class="['nav-item', { 'nav-item--active': isActive(i.to) }]"
        >
          <span class="nav-bullet" aria-hidden="true" />
          <span class="nav-label">{{ i.label }}</span>
        </RouterLink>
      </nav>

      <footer class="sidebar-foot">
        <div class="user">
          <div class="user-name">{{ auth.user?.full_name || auth.user?.phone || '—' }}</div>
          <div class="user-role">{{ ROLE_UZ[auth.role || ''] || auth.role }}</div>
        </div>
        <button class="logout" @click="logout">Chiqish</button>
      </footer>
    </aside>

    <div class="main">
      <header class="topbar">
        <h2 class="topbar-title">{{ currentTitle }}</h2>
        <div class="topbar-right">
          <div class="ws" :class="{ 'ws--ok': ws.connected }">
            <span class="ws-dot" />
            {{ ws.connected ? 'Jonli' : 'Aloqasiz' }}
          </div>
        </div>
      </header>
      <section class="content">
        <RouterView />
      </section>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr;
  height: 100vh;
  background: var(--bg);
}

.sidebar {
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px 20px;
  height: var(--topbar-height);
  border-bottom: 1px solid var(--border);
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
  letter-spacing: -0.018em;
  color: var(--ink-900);
}

.nav {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--ink-600);
  transition: background var(--motion-fast) var(--motion-ease),
              color var(--motion-fast) var(--motion-ease);
}
.nav-item:hover {
  background: var(--bg-subtle);
  color: var(--foreground);
  text-decoration: none;
}
.nav-item--active {
  background: var(--primary-soft-2);
  color: var(--primary-strong);
}
.nav-item--active .nav-bullet { background: var(--primary); }
.nav-bullet {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ink-200);
  flex: 0 0 6px;
}
.sidebar-foot {
  border-top: 1px solid var(--border);
  padding: 14px;
}
.user { padding: 0 4px 10px; }
.user-name { font-size: var(--font-size-sm); font-weight: 600; color: var(--ink-800); }
.user-role { font-size: var(--font-size-xs); color: var(--muted-fg); margin-top: 2px; }

.logout {
  width: 100%;
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  background: var(--bg-subtle);
  color: var(--ink-600);
  font-weight: 500;
  font-size: var(--font-size-sm);
  border: 1px solid var(--border);
  text-align: left;
  transition: background var(--motion-fast) var(--motion-ease);
}
.logout:hover { background: var(--primary-soft-2); color: var(--primary-strong); }

.main {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.topbar {
  height: var(--topbar-height);
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
}
.topbar-title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.015em;
  color: var(--ink-900);
}
.topbar-right { display: flex; align-items: center; gap: 16px; }

.ws {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-xs);
  color: var(--muted-fg);
  padding: 4px 10px;
  border-radius: var(--radius-full);
  background: var(--bg-subtle);
  border: 1px solid var(--border);
}
.ws-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--danger); }
.ws--ok {
  background: color-mix(in srgb, var(--success) 10%, transparent);
  color: var(--success);
  border-color: color-mix(in srgb, var(--success) 22%, transparent);
}
.ws--ok .ws-dot { background: var(--success); }

.content {
  padding: 24px;
  overflow: auto;
  flex: 1;
}
</style>
