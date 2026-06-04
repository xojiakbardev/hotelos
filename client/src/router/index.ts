import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { Role } from '@/api/auth'

// Forms are NEVER separate routes — they always open as a Modal from the
// parent list page. See feedback-ui-page-structure.
const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true, layout: 'blank' }
  },
  {
    path: '/guest',
    component: () => import('@/layouts/GuestLayout.vue'),
    meta: { roles: ['guest'] },
    children: [
      { path: '', name: 'guest-dashboard', component: () => import('@/views/GuestDashboard.vue') },
      { path: 'change-password', name: 'guest-change-password', component: () => import('@/views/GuestChangePassword.vue') }
    ]
  },
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    children: [
      { path: '', name: 'dashboard', component: () => import('@/views/Dashboard.vue'), meta: { roles: ['manager', 'reception', 'cleaner'] } },
      {
        path: 'rooms',
        name: 'rooms',
        component: () => import('@/views/RoomsList.vue'),
        meta: { roles: ['manager', 'reception', 'cleaner', 'technician'], title: 'Xonalar' }
      },
      {
        path: 'guests',
        name: 'guests',
        component: () => import('@/views/GuestsList.vue'),
        meta: { roles: ['manager', 'reception'], title: 'Mehmonlar' }
      },
      {
        path: 'guests/history/:phone',
        name: 'guest-history',
        component: () => import('@/views/GuestHistory.vue'),
        meta: { roles: ['manager', 'reception'], title: 'Mehmon tarixi' }
      },
      {
        path: 'orders',
        name: 'orders',
        component: () => import('@/views/OrdersList.vue'),
        meta: { roles: ['manager', 'reception'], title: 'Xona xizmati' }
      },
      {
        path: 'housekeeping',
        name: 'housekeeping',
        component: () => import('@/views/HousekeepingQueue.vue'),
        meta: { roles: ['manager', 'cleaner'], title: 'Tozalash' }
      },
      {
        path: 'maintenance',
        name: 'maintenance',
        component: () => import('@/views/MaintenanceQueue.vue'),
        meta: { roles: ['manager', 'technician', 'reception'], title: 'Texnik xizmat' }
      },
      {
        path: 'staff',
        name: 'staff',
        component: () => import('@/views/StaffList.vue'),
        meta: { roles: ['manager'], title: 'Xodimlar' }
      },
      {
        path: 'menu',
        name: 'menu',
        component: () => import('@/views/MenuList.vue'),
        meta: { roles: ['manager'], title: 'Menyu' }
      },
      {
        path: 'audit-logs',
        name: 'audit-logs',
        component: () => import('@/views/AuditLogs.vue'),
        meta: { roles: ['manager'], title: 'Audit log' }
      }
    ]
  },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFound.vue') }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  auth.restoreFromStorage()

  if (to.meta.public) return true
  if (!auth.isAuthenticated) return { name: 'login', query: { next: to.fullPath } }

  // Guest users can only access /guest routes
  if (auth.role === 'guest') {
    if (to.path.startsWith('/guest')) {
      // If must change password, force to change-password page
      if (auth.mustChangePassword && to.name !== 'guest-change-password') {
        return { name: 'guest-change-password' }
      }
      return true
    }
    return { name: 'guest-dashboard' }
  }

  // Staff users cannot access /guest portal routes
  if (to.path === '/guest' || to.path.startsWith('/guest/')) {
    return { name: 'dashboard' }
  }

  const allowed = (to.meta.roles as Role[] | undefined) ?? null
  if (allowed && auth.role && !allowed.includes(auth.role)) {
    // Redirect each role to their home page
    if (auth.role === 'technician') return { name: 'maintenance' }
    if (auth.role === 'cleaner') return { name: 'housekeeping' }
    return { name: 'dashboard' }
  }
  return true
})

export default router
