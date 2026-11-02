import { ElMessage } from 'element-plus'
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import AdminLayout from '@/layouts/AdminLayout.vue'
import ShopLayout from '@/layouts/ShopLayout.vue'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    requiresAdmin?: boolean
    guestOnly?: boolean
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/auth/RegisterView.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/',
    component: ShopLayout,
    children: [
      {
        path: '',
        name: 'products',
        component: () => import('@/views/shop/ProductListView.vue'),
      },
      {
        path: 'products/:id',
        name: 'product-detail',
        component: () => import('@/views/shop/ProductDetailView.vue'),
        props: true,
      },
      {
        path: 'cart',
        name: 'cart',
        component: () => import('@/views/shop/CartView.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'orders',
        name: 'orders',
        component: () => import('@/views/shop/OrderListView.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'orders/:id',
        name: 'order-detail',
        component: () => import('@/views/shop/OrderDetailView.vue'),
        props: true,
        meta: { requiresAuth: true },
      },
    ],
  },
  {
    path: '/admin',
    component: AdminLayout,
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      { path: '', redirect: '/admin/products' },
      {
        path: 'products',
        name: 'admin-products',
        component: () => import('@/views/admin/AdminProductsView.vue'),
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    ElMessage.error('需要管理员权限')
    return { path: '/' }
  }
  if (to.meta.guestOnly && auth.token) {
    return { path: '/' }
  }
  return true
})

export default router
