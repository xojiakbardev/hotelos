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
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    children: [
      { path: '', name: 'dashboard', component: () => import('@/views/Dashboard.vue') },
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
        path: 'reservations',
        name: 'reservations',
        component: () => import('@/views/ReservationsList.vue'),
        meta: { roles: ['manager', 'reception'], title: 'Bronlar' }
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

  const allowed = (to.meta.roles as Role[] | undefined) ?? null
  if (allowed && auth.role && !allowed.includes(auth.role)) {
    return { name: 'dashboard' }
  }
  return true
})

export default router
