<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useWsStore } from '@/stores/ws'
import { Button } from '@/components/ui/button'
import { Sheet, SheetTrigger, SheetContent } from '@/components/ui/sheet'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuLabel } from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  DoorOpen,
  Users,
  UtensilsCrossed,
  Sparkles,
  Wrench,
  UserCog,
  ScrollText,
  LogOut,
  Menu,
  Wifi,
  WifiOff,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const ws = useWsStore()
const mobileOpen = ref(false)
const sidebarCollapsed = ref(false)

interface NavItem { to: string; label: string; roles: string[]; icon: any }

const NAV: NavItem[] = [
  { to: '/',              label: 'Boshqaruv paneli', roles: ['manager', 'reception', 'cleaner'], icon: LayoutDashboard },
  { to: '/rooms',         label: 'Xonalar',          roles: ['manager', 'reception', 'cleaner', 'technician'], icon: DoorOpen },
  { to: '/guests',        label: 'Mehmonlar',        roles: ['manager', 'reception'], icon: Users },
  { to: '/orders',        label: 'Xona xizmati',     roles: ['manager', 'reception'], icon: UtensilsCrossed },
  { to: '/housekeeping',  label: 'Tozalash',         roles: ['manager', 'cleaner'], icon: Sparkles },
  { to: '/maintenance',   label: 'Texnik xizmat',    roles: ['manager', 'technician', 'reception'], icon: Wrench },
  { to: '/staff',         label: 'Xodimlar',         roles: ['manager'], icon: UserCog },
  { to: '/audit-logs',    label: 'Audit log',        roles: ['manager'], icon: ScrollText },
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
  return (route.meta.title as string) || ''
})

const userInitials = computed(() => {
  const name = auth.user?.full_name || auth.user?.phone || ''
  if (!name) return '?'
  const parts = name.split(' ')
  return parts.length > 1
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase()
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

function navigateMobile(to: string) {
  mobileOpen.value = false
  router.push(to)
}
</script>

<template>
  <div class="flex h-screen bg-background">
    <!-- Desktop Sidebar -->
    <aside
      :class="cn(
        'hidden md:flex flex-col border-r bg-card transition-all duration-200',
        sidebarCollapsed ? 'w-16' : 'w-64'
      )"
    >
      <!-- Brand -->
      <div class="flex items-center gap-3 px-3 h-16 border-b" :class="sidebarCollapsed ? 'justify-center' : 'px-5'">
        <div class="w-9 h-9 rounded-lg bg-primary text-primary-foreground grid place-items-center font-bold text-sm shadow-sm shrink-0">
          H
        </div>
        <span v-if="!sidebarCollapsed" class="font-semibold text-base tracking-tight">HotelOS</span>
      </div>

      <!-- Nav -->
      <nav class="flex-1 overflow-y-auto p-2 space-y-1">
        <RouterLink
          v-for="item in items"
          :key="item.to"
          :to="item.to"
          :title="sidebarCollapsed ? item.label : undefined"
          :class="cn(
            'flex items-center rounded-md transition-colors cursor-pointer',
            sidebarCollapsed ? 'justify-center h-10 w-full' : 'gap-3 px-3 py-2.5 text-sm font-medium',
            isActive(item.to)
              ? 'bg-primary/10 text-primary'
              : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
          )"
        >
          <component :is="item.icon" :class="sidebarCollapsed ? 'w-5 h-5' : 'w-4 h-4'" />
          <span v-if="!sidebarCollapsed">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <!-- Collapse toggle -->
      <div class="border-t p-2">
        <Button
          variant="ghost"
          :size="sidebarCollapsed ? 'icon-sm' : 'sm'"
          :class="sidebarCollapsed ? 'w-full justify-center' : 'w-full justify-start gap-2'"
          @click="sidebarCollapsed = !sidebarCollapsed"
        >
          <component :is="sidebarCollapsed ? PanelLeftOpen : PanelLeftClose" class="w-4 h-4" />
          <span v-if="!sidebarCollapsed" class="text-xs text-muted-foreground">Yig'ish</span>
        </Button>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Top bar -->
      <header class="h-16 border-b bg-card flex items-center justify-between px-4 md:px-6 shrink-0">
        <div class="flex items-center gap-3">
          <!-- Mobile menu trigger -->
          <Sheet v-model:open="mobileOpen">
            <SheetTrigger as-child>
              <Button variant="ghost" size="icon-sm" class="md:hidden">
                <Menu class="w-5 h-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" class="w-64 p-0">
              <div class="flex items-center gap-3 px-5 h-16 border-b">
                <div class="w-9 h-9 rounded-lg bg-primary text-primary-foreground grid place-items-center font-bold text-sm">
                  H
                </div>
                <span class="font-semibold text-base tracking-tight">HotelOS</span>
              </div>
              <nav class="p-3 space-y-1">
                <button
                  v-for="item in items"
                  :key="item.to"
                  :class="cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors w-full text-left cursor-pointer',
                    isActive(item.to)
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  )"
                  @click="navigateMobile(item.to)"
                >
                  <component :is="item.icon" class="w-4 h-4" />
                  {{ item.label }}
                </button>
              </nav>
            </SheetContent>
          </Sheet>

          <!-- WiFi indicator -->
          <div
            :class="cn(
              'flex items-center gap-1.5 text-xs px-2 py-1 rounded-full border',
              ws.connected
                ? 'bg-success/10 text-green-700 border-success/20'
                : 'bg-muted text-muted-foreground border-border'
            )"
          >
            <component :is="ws.connected ? Wifi : WifiOff" class="w-3 h-3" />
          </div>

          <h1 class="text-base font-semibold tracking-tight">{{ currentTitle }}</h1>
        </div>

        <!-- Right: profile dropdown -->
        <div class="flex items-center gap-3">
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button variant="ghost" class="flex items-center gap-2 h-auto py-1.5 px-2 cursor-pointer">
                <Avatar class="h-8 w-8">
                  <AvatarFallback class="text-xs bg-primary/10 text-primary">{{ userInitials }}</AvatarFallback>
                </Avatar>
                <div class="hidden sm:block text-left">
                  <p class="text-sm font-medium leading-none">{{ auth.user?.full_name || auth.user?.phone || '—' }}</p>
                  <p class="text-xs text-muted-foreground">{{ ROLE_UZ[auth.role || ''] || auth.role }}</p>
                </div>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" class="w-48">
              <DropdownMenuLabel>
                <p class="font-medium">{{ auth.user?.full_name || auth.user?.phone }}</p>
                <p class="text-xs text-muted-foreground font-normal">{{ ROLE_UZ[auth.role || ''] || auth.role }}</p>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem @click="logout" class="text-destructive focus:text-destructive">
                <LogOut class="w-4 h-4 mr-2" />
                Chiqish
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      <!-- Page content -->
      <main class="flex-1 overflow-y-auto p-4 md:p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>
