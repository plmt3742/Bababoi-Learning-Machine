<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { IconDown, IconPoweroff } from '@arco-design/web-vue/es/icon'
import { useAuthStore } from '../../stores/auth'
import BrandMark from './BrandMark.vue'
import { accountNavigation, topNavigation } from './navigation'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activeKey = computed(() => route.meta.navKey)
const pageTitle = computed(() => route.meta.title ?? '错题学习机')
const displayName = computed(() => auth.user?.username ?? '已登录')
const initial = computed(() => displayName.value.slice(0, 1).toUpperCase())

function handleNavigate(to: string): void {
  void router.push(to)
}

async function handleLogout(): Promise<void> {
  auth.logout()
  await router.push('/login')
}
</script>

<template>
  <header class="appbar">
    <RouterLink class="appbar__brand" to="/" aria-label="Bababoi 首页">
      <BrandMark :size="20" />
      <span class="appbar__word">Bababoi</span>
      <span class="appbar__sep" aria-hidden="true" />
      <small>错题学习机</small>
    </RouterLink>

    <span class="appbar__current">{{ pageTitle }}</span>

    <nav class="appbar__nav" aria-label="主要导航">
      <RouterLink
        v-for="item in topNavigation"
        :key="item.key"
        :to="item.to"
        :aria-current="activeKey === item.key ? 'page' : undefined"
      >
        {{ item.label }}
      </RouterLink>
    </nav>

    <div class="appbar__right">
      <a-dropdown v-if="auth.isAuthenticated" trigger="click" position="br">
        <button class="appbar__user" type="button" aria-label="账号菜单">
          <span class="user__avatar" aria-hidden="true">{{ initial }}</span>
          <span class="user__name">{{ displayName }}</span>
          <IconDown class="user__chevron" aria-hidden="true" />
        </button>
        <template #content>
          <a-doption
            v-for="item in accountNavigation"
            :key="item.key"
            @click="handleNavigate(item.to)"
          >
            <template #icon>
              <component :is="item.icon" />
            </template>
            {{ item.label }}
          </a-doption>
          <a-doption @click="handleLogout">
            <template #icon>
              <IconPoweroff />
            </template>
            退出登录
          </a-doption>
        </template>
      </a-dropdown>

      <RouterLink v-else class="appbar__login" to="/login">登录</RouterLink>
    </div>
  </header>
</template>

<style scoped>
.appbar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  height: var(--layout-topbar-height);
  padding: 0 var(--space-5);
  border-bottom: 1px solid var(--color-border);
  border-radius: var(--radius-frame) var(--radius-frame) 0 0;
  background: var(--color-surface);
}

.appbar__brand {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  flex: none;
  color: var(--color-text-1);
  font-size: 15px;
  line-height: 22px;
}

.appbar__brand:hover {
  color: var(--color-text-1);
}

.appbar__word {
  font-weight: 650;
  letter-spacing: 0.005em;
}

.appbar__sep {
  width: 1px;
  height: 15px;
  background: var(--color-border-strong);
}

.appbar__brand small {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  font-weight: 400;
  letter-spacing: 0.01em;
}

.appbar__current {
  display: none;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.appbar__nav {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: var(--space-2);
}

.appbar__nav a {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 10px;
  border-radius: var(--radius-sm);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  white-space: nowrap;
}

.appbar__nav a:hover {
  background: var(--color-bg);
  color: var(--color-text-1);
}

.appbar__nav a[aria-current='page'] {
  background: var(--color-primary-soft);
  color: var(--color-primary-active);
  font-weight: 600;
}

.appbar__right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-left: auto;
}

.appbar__login {
  color: var(--color-primary-active);
  font-size: var(--text-sm);
  font-weight: 500;
}

.appbar__user {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.user__avatar {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary-active);
  font-size: var(--text-sm);
  font-weight: 650;
  line-height: 1;
}

.user__name {
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user__chevron {
  width: 14px;
  height: 14px;
  color: var(--color-text-3);
}

@media (max-width: 1023px) {
  .appbar {
    gap: var(--space-3);
    padding: 0 var(--space-4);
  }

  .appbar__sep,
  .appbar__brand small {
    display: none;
  }

  .appbar__nav {
    margin-left: 0;
    gap: 0;
  }

  .appbar__nav a {
    padding: 0 8px;
  }

  .user__name {
    max-width: 96px;
  }
}

@media (max-width: 767px) {
  .appbar {
    height: var(--layout-mobile-header-height);
    gap: 10px;
    padding: 0 var(--space-4);
    border-radius: 8px 8px 0 0;
  }

  .appbar__brand {
    font-size: var(--text-sm);
  }

  .appbar__brand small,
  .appbar__sep,
  .appbar__nav {
    display: none;
  }

  .appbar__current {
    display: inline;
  }

  .user__name,
  .user__chevron {
    display: none;
  }

  .user__avatar {
    width: 26px;
    height: 26px;
    font-size: var(--text-sm);
  }
}
</style>
