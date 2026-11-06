import { createRouter, createWebHistory } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import { useAuthStore } from '../stores/auth'
import { pinia } from '../stores'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { title: '登录' },
    },
    {
      path: '/',
      component: AppShell,
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('../views/HomeView.vue'),
          meta: { title: '首页', navKey: 'home', requiresAuth: true },
        },
        {
          path: 'questions',
          name: 'questions',
          component: () => import('../views/QuestionListView.vue'),
          meta: { title: '错题本', navKey: 'questions', requiresAuth: true },
        },
        {
          path: 'questions/new',
          name: 'question-new',
          component: () => import('../views/QuestionCreateView.vue'),
          meta: { title: '录入错题', navKey: 'create', requiresAuth: true },
        },
        {
          path: 'tasks',
          name: 'tasks',
          component: () => import('../views/TaskCenterView.vue'),
          meta: { title: '任务中心', navKey: 'tasks', requiresAuth: true },
        },
        {
          path: 'questions/:id',
          name: 'question-detail',
          component: () => import('../views/QuestionDetailView.vue'),
          meta: { title: '错题详情', navKey: 'questions', requiresAuth: true },
        },
        {
          path: 'practice/:id?',
          name: 'practice',
          component: () => import('../views/PracticeView.vue'),
          meta: { title: '练习', navKey: 'practice', requiresAuth: true },
        },
        {
          path: 'stats',
          name: 'stats',
          component: () => import('../views/StatsView.vue'),
          meta: { title: '统计', navKey: 'stats', requiresAuth: true },
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('../views/SettingsView.vue'),
          meta: { title: '设置', requiresAuth: true },
        },
        {
          path: ':pathMatch(.*)*',
          name: 'not-found',
          component: () => import('../views/NotFoundView.vue'),
          meta: { title: '页面不存在', requiresAuth: true },
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore(pinia)

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }

  if (auth.isAuthenticated && to.name === 'login') {
    return { name: 'home' }
  }

  return true
})

router.afterEach((to) => {
  document.title = to.meta.title
    ? `${to.meta.title} · Bababoi Learning Machine`
    : 'Bababoi Learning Machine'
})

export default router
