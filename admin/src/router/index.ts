import { createRouter, createWebHistory } from 'vue-router'

import AdminShell from '../layouts/AdminShell.vue'
import { pinia } from '../stores'
import { useAdminAuth } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { title: '管理端登录' },
    },
    {
      path: '/',
      component: AdminShell,
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('../views/DashboardView.vue'),
          meta: { title: '运营总览', group: '监控', requiresAuth: true },
        },
        {
          path: 'users',
          name: 'users',
          component: () => import('../views/UsersView.vue'),
          meta: { title: '用户管理', group: '运营', requiresAuth: true },
        },
        {
          path: 'password-requests',
          name: 'password-requests',
          component: () => import('../views/PasswordRequestsView.vue'),
          meta: { title: '密码申请', group: '运营', requiresAuth: true },
        },
        {
          path: 'questions',
          name: 'questions',
          component: () => import('../views/QuestionsView.vue'),
          meta: { title: '内容管理', group: '运营', requiresAuth: true },
        },
        {
          path: 'tasks',
          name: 'tasks',
          component: () => import('../views/TasksView.vue'),
          meta: { title: '任务中心', group: 'AI 运维', requiresAuth: true },
        },
        {
          path: 'ai-logs',
          name: 'ai-logs',
          component: () => import('../views/AiLogsView.vue'),
          meta: { title: 'AI 调用日志', group: 'AI 运维', requiresAuth: true },
        },
        {
          path: 'audit',
          name: 'audit',
          component: () => import('../views/AuditView.vue'),
          meta: { title: '审计日志', group: '审计', requiresAuth: true },
        },
        {
          path: 'alerts',
          name: 'alerts',
          component: () => import('../views/AlertsView.vue'),
          meta: { title: '告警中心', group: '监控', requiresAuth: true },
        },
        {
          path: 'system',
          name: 'system',
          component: () => import('../views/SystemView.vue'),
          meta: { title: '系统健康', group: '系统', requiresAuth: true },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAdminAuth(pinia)
  if (to.meta.requiresAuth) {
    const authenticated = await auth.ensureSession()
    if (!authenticated) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    return true
  }
  if (to.name === 'login' && auth.token) {
    const authenticated = await auth.ensureSession()
    if (authenticated) return { name: 'dashboard' }
  }
  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · Bababoi Admin` : 'Bababoi Admin'
})

export default router
