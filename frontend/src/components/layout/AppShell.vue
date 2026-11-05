<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import AppSidebar from './AppSidebar.vue'
import AppTopBar from './AppTopBar.vue'
import { primaryNavigation } from './navigation'

const route = useRoute()
const drawerOpen = ref(false)
const activeKey = computed(() => route.meta.navKey)

watch(
  () => route.fullPath,
  () => {
    drawerOpen.value = false
  },
)
</script>

<template>
  <div class="app-shell">
    <a class="app-shell__skip-link" href="#main-content">跳到主要内容</a>

    <aside class="app-shell__sidebar">
      <AppSidebar />
    </aside>

    <div class="app-shell__main">
      <AppTopBar @open-menu="drawerOpen = true" />
      <main id="main-content" class="app-shell__content" tabindex="-1">
        <div class="app-shell__content-inner">
          <RouterView />
        </div>
      </main>
    </div>

    <a-drawer
      v-model:visible="drawerOpen"
      title="导航菜单"
      placement="left"
      :width="280"
      :footer="false"
      :body-style="{ padding: '0' }"
      unmount-on-close
    >
      <AppSidebar in-drawer @navigate="drawerOpen = false" />
    </a-drawer>

    <nav class="app-shell__bottom-nav" aria-label="快捷导航">
      <RouterLink
        v-for="item in primaryNavigation"
        :key="item.key"
        :to="item.to"
        class="app-shell__bottom-link"
        :class="{ 'app-shell__bottom-link--active': activeKey === item.key }"
        :aria-current="activeKey === item.key ? 'page' : undefined"
      >
        <component :is="item.icon" class="app-shell__bottom-icon" aria-hidden="true" />
        <span class="app-shell__bottom-label">{{ item.label }}</span>
      </RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
  background: var(--color-bg);
}

.app-shell__skip-link {
  position: fixed;
  top: var(--space-2);
  left: var(--space-2);
  z-index: calc(var(--z-topbar) + 1);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  box-shadow: var(--shadow-pop);
  color: var(--color-primary);
  transform: translateY(-200%);
}

.app-shell__skip-link:focus-visible {
  transform: translateY(0);
}

.app-shell__sidebar {
  position: sticky;
  top: 0;
  z-index: var(--z-sidebar);
  flex: 0 0 var(--layout-sidebar-width);
  width: var(--layout-sidebar-width);
  height: 100vh;
  border-right: 1px solid var(--color-border);
  background: var(--color-surface);
}

.app-shell__main {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.app-shell__content {
  flex: 1;
  padding: var(--space-5) var(--layout-gutter) var(--space-8);
}

.app-shell__content:focus {
  outline: none;
}

.app-shell__content-inner {
  width: 100%;
  max-width: var(--layout-content-max);
  margin: 0 auto;
}

.app-shell__bottom-nav {
  display: none;
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: var(--z-topbar);
  padding-bottom: env(safe-area-inset-bottom);
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}

.app-shell__bottom-link {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  min-height: var(--layout-bottom-nav-height);
  color: var(--color-text-2);
  font-size: var(--text-xs);
  line-height: 1.35;
}

.app-shell__bottom-link--active {
  color: var(--color-primary);
}

.app-shell__bottom-icon {
  width: var(--icon-md);
  height: var(--icon-md);
}

@media (max-width: 1199px) {
  .app-shell__sidebar {
    display: none;
  }

  .app-shell__content {
    padding: var(--space-5) var(--space-5) var(--space-8);
  }
}

@media (max-width: 767px) {
  .app-shell__content {
    padding: var(--space-4) var(--layout-gutter-mobile)
      calc(var(--layout-bottom-nav-height) + env(safe-area-inset-bottom) + var(--space-6));
  }

  .app-shell__bottom-nav {
    display: flex;
  }
}
</style>
