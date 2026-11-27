<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'

import AppIcon from '../components/AppIcon.vue'
import { useAdminAuth } from '../stores/auth'
import { useAdminData } from '../stores/adminData'

type IconName =
  | 'dashboard'
  | 'alert'
  | 'users'
  | 'key'
  | 'file'
  | 'tasks'
  | 'spark'
  | 'audit'
  | 'system'

interface NavItem {
  label: string
  to: string
  icon: IconName
  badge?: number
  badgeTone?: 'default' | 'danger'
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const route = useRoute()
const router = useRouter()
const auth = useAdminAuth()
const data = useAdminData()
const sidebarOpen = ref(false)

const navGroups = computed<NavGroup[]>(() => [
  {
    label: '监控',
    items: [
      { label: '运营总览', to: '/', icon: 'dashboard' },
      {
        label: '告警中心',
        to: '/alerts',
        icon: 'alert',
        badge: data.activeAlertCount,
        badgeTone: 'danger',
      },
    ],
  },
  {
    label: '运营',
    items: [
      { label: '用户管理', to: '/users', icon: 'users' },
      { label: '密码申请', to: '/password-requests', icon: 'key', badge: data.pendingPasswordCount },
      { label: '内容管理', to: '/questions', icon: 'file' },
    ],
  },
  {
    label: 'AI 运维',
    items: [
      {
        label: '任务中心',
        to: '/tasks',
        icon: 'tasks',
        badge: data.failedTaskCount,
        badgeTone: 'danger',
      },
      { label: 'AI 调用日志', to: '/ai-logs', icon: 'spark' },
    ],
  },
  {
    label: '审计',
    items: [{ label: '审计日志', to: '/audit', icon: 'audit' }],
  },
  {
    label: '系统',
    items: [{ label: '系统健康', to: '/system', icon: 'system' }],
  },
])

const currentTitle = computed(() => String(route.meta.title ?? '运营总览'))
const currentGroup = computed(() => String(route.meta.group ?? '监控'))
const adminName = computed(() => auth.user?.username ?? 'admin')
const adminInitial = computed(() => adminName.value.slice(0, 1).toUpperCase())
const nowText = computed(() =>
  new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date()),
)

const environmentLabel = computed(() => {
  const system = data.system
  if (!system) return ''
  if (system.environment.is_demo) return '演示环境'
  if (system.environment.app_env === 'production') return '生产环境'
  if (system.environment.app_env === 'staging') return '预发布环境'
  return '开发环境'
})

const environmentSummary = computed(() => {
  const system = data.system
  if (!system) return '环境信息未获取'
  return `${environmentLabel.value} · LLM ${system.environment.llm_mode}`
})

function isActive(item: NavItem): boolean {
  return route.path === item.to
}

async function handleLogout(): Promise<void> {
  await auth.logout()
  await router.push('/login')
}

watch(
  () => route.fullPath,
  () => {
    sidebarOpen.value = false
  },
)

onMounted(async () => {
  const loaded = await data.loadAll()
  if (!loaded) {
    Message.error('部分管理数据加载失败，请检查后端服务')
  }
})
</script>

<template>
  <div class="adm-shell">
    <div class="adm-frame">
      <header class="adm-topbar">
        <button class="adm-menu-btn" type="button" aria-label="打开导航" @click="sidebarOpen = true">
          <AppIcon name="menu" :size="17" />
        </button>

        <RouterLink class="adm-brand" to="/" aria-label="Bababoi 管理端首页">
          <span class="adm-brand__mark" aria-hidden="true">
            <span v-for="index in 9" :key="index" />
          </span>
          <div class="adm-brand__copy">
            <strong>Bababoi</strong>
            <span>Admin</span>
          </div>
        </RouterLink>

        <span class="adm-topbar__divider" aria-hidden="true" />

        <div class="adm-breadcrumb">
          <span>{{ currentGroup }}</span>
          <AppIcon name="chevron" :size="12" />
          <strong>{{ currentTitle }}</strong>
        </div>

        <div class="adm-topbar__right">
          <span v-if="environmentLabel" class="adm-env">{{ environmentLabel }}</span>
          <span class="adm-clock">{{ nowText }}</span>
          <button class="adm-icon-btn" type="button" aria-label="通知">
            <AppIcon name="bell" :size="17" />
            <span class="adm-icon-btn__dot" />
          </button>
          <span class="adm-topbar__user">
            <span class="adm-avatar">{{ adminInitial }}</span>
            <span>{{ adminName }}</span>
          </span>
          <button class="adm-icon-btn" type="button" aria-label="退出登录" @click="handleLogout">
            <AppIcon name="logout" :size="16" />
          </button>
        </div>
      </header>

      <div class="adm-body">
        <div v-if="sidebarOpen" class="adm-sidebar-scrim" @click="sidebarOpen = false" />

        <aside class="adm-sidebar" :class="{ 'is-open': sidebarOpen }">
          <nav class="adm-nav" aria-label="管理端导航">
            <div v-for="group in navGroups" :key="group.label" class="adm-nav__group">
              <p class="adm-nav__label">{{ group.label }}</p>
              <RouterLink
                v-for="item in group.items"
                :key="item.to"
                :to="item.to"
                class="adm-nav__link"
                :class="{ 'is-active': isActive(item) }"
              >
                <AppIcon :name="item.icon" :size="16" />
                <span>{{ item.label }}</span>
                <span
                  v-if="item.badge"
                  class="adm-nav__badge"
                  :class="{ 'adm-nav__badge--danger': item.badgeTone === 'danger' }"
                >
                  {{ item.badge }}
                </span>
              </RouterLink>
            </div>
          </nav>

          <div class="adm-sidebar__foot">
            <div class="adm-sidebar__env"><i /> {{ environmentSummary }}</div>
            <div class="adm-sidebar__user">
              <span class="adm-avatar">{{ adminInitial }}</span>
              <div>
                <strong>{{ adminName }}</strong>
                <span>系统管理员</span>
              </div>
            </div>
          </div>
        </aside>

        <main class="adm-content">
          <RouterView />
        </main>
      </div>
    </div>
  </div>
</template>
