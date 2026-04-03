import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { guest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/RegisterView.vue'),
    meta: { guest: true },
  },
  {
    path: '/',
    component: () => import('../components/layout/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'Dashboard', component: () => import('../views/DashboardView.vue') },
      { path: 'heart', name: 'Heart', component: () => import('../views/HeartView.vue') },
      { path: 'sleep', name: 'Sleep', component: () => import('../views/SleepView.vue') },
      { path: 'activity', name: 'Activity', component: () => import('../views/ActivityView.vue') },
      { path: 'workouts', name: 'Workouts', component: () => import('../views/WorkoutsView.vue') },
      { path: 'chat', name: 'AIChat', component: () => import('../views/AIChatView.vue') },
      { path: 'agents', name: 'Agents', component: () => import('../views/AgentBuilderView.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.meta.guest && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
