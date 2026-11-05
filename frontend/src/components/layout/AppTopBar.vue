<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { IconDown, IconMenu, IconPoweroff, IconUser } from '@arco-design/web-vue/es/icon'
import { useAuthStore } from '../../stores/auth'

const emit = defineEmits<{ openMenu: [] }>()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const pageTitle = computed(() => route.meta.title)
const displayName = computed(() => auth.user?.username ?? '已登录')

async function handleLogout(): Promise<void> {
  auth.logout()
  await router.push('/login')
}
</script>

<template>
  <header class="app-topbar">
    <a-button
      class="app-topbar__menu"
      type="text"
      size="large"
      aria-label="打开导航菜单"
      @click="emit('openMenu')"
    >
      <template #icon>
        <IconMenu />
      </template>
    </a-button>

    <div class="app-topbar__context">
      <span class="app-topbar__product">错题巩固 · 学习机器</span>
      <span class="app-topbar__title">{{ pageTitle }}</span>
    </div>

    <div class="app-topbar__auth">
      <a-dropdown v-if="auth.isAuthenticated" trigger="click" position="br">
        <a-button class="app-topbar__user" type="text" aria-label="账号菜单">
          <template #icon>
            <IconUser />
          </template>
          <span class="app-topbar__username">{{ displayName }}</span>
          <IconDown class="app-topbar__chevron" aria-hidden="true" />
        </a-button>
        <template #content>
          <a-doption @click="handleLogout">
            <template #icon>
              <IconPoweroff />
            </template>
            退出登录
          </a-doption>
        </template>
      </a-dropdown>

      <RouterLink v-else class="app-topbar__login" to="/login">登录</RouterLink>
    </div>
  </header>
</template>

<style scoped>
.app-topbar {
  position: sticky;
  top: 0;
  z-index: var(--z-topbar);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: var(--layout-topbar-height);
  padding: 0 var(--layout-gutter);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}

.app-topbar__menu {
  display: none;
  flex: none;
  color: var(--color-text-2);
}

.app-topbar__context {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.app-topbar__product {
  color: var(--color-text-3);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
  letter-spacing: 0.04em;
}

.app-topbar__title {
  overflow: hidden;
  color: var(--color-text-1);
  font-size: var(--text-base);
  font-weight: 600;
  line-height: 1.375;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-topbar__auth {
  display: flex;
  flex: none;
  align-items: center;
  min-width: 0;
}

.app-topbar__login {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--control-height);
  padding: 0 var(--space-3);
  border-radius: var(--radius-sm);
  color: var(--color-primary);
  font-size: var(--text-sm);
  font-weight: 500;
}

.app-topbar__login:hover {
  background: var(--color-primary-soft);
  color: var(--color-primary-active);
}

.app-topbar__user {
  max-width: 200px;
  color: var(--color-text-2);
}

.app-topbar__username {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-topbar__chevron {
  width: var(--icon-sm);
  height: var(--icon-sm);
  margin-left: var(--space-1);
  color: var(--color-text-3);
}

@media (max-width: 1199px) {
  .app-topbar__menu {
    display: inline-flex;
  }
}

@media (max-width: 767px) {
  .app-topbar {
    gap: var(--space-2);
    padding: 0 var(--space-2);
  }

  .app-topbar__product {
    display: none;
  }

  .app-topbar__user {
    max-width: 128px;
  }

  .app-topbar__username {
    max-width: 80px;
  }

  .app-topbar__chevron {
    display: none;
  }
}
</style>
