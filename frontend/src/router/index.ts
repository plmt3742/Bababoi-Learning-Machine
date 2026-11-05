import { createRouter, createWebHistory } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'

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
          meta: { title: '首页', navKey: 'home' },
        },
        {
          path: 'questions',
          name: 'questions',
          component: () => import('../views/QuestionListView.vue'),
          meta: { title: '错题本', navKey: 'questions' },
        },
        {
          path: 'questions/new',
          name: 'question-new',
          component: () => import('../views/QuestionCreateView.vue'),
          meta: { title: '录入错题', navKey: 'questions' },
        },
        {
          path: 'tasks',
          name: 'tasks',
          component: () => import('../views/TaskCenterView.vue'),
          meta: { title: '任务中心', navKey: 'tasks' },
        },
        {
          path: 'questions/:id',
          name: 'question-detail',
          component: () => import('../views/QuestionDetailView.vue'),
          meta: { title: '错题详情', navKey: 'questions' },
        },
        {
          path: 'practice/:id?',
          name: 'practice',
          component: () => import('../views/PracticeView.vue'),
          meta: { title: '练习', navKey: 'practice' },
        },
        {
          path: 'stats',
          name: 'stats',
          component: () => import('../views/StatsView.vue'),
          meta: { title: '统计', navKey: 'stats' },
        },
        {
          path: ':pathMatch(.*)*',
          name: 'not-found',
          component: () => import('../views/NotFoundView.vue'),
          meta: { title: '页面不存在' },
        },
      ],
    },
  ],
})

router.afterEach((to) => {
  document.title = to.meta.title
    ? `${to.meta.title} · Bababoi Learning Machine`
    : 'Bababoi Learning Machine'
})

export default router
