<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import AppTopBar from './AppTopBar.vue'
import { mobileNavigation } from './navigation'

const route = useRoute()
const activeKey = computed(() => route.meta.navKey)
const isWorkspace = computed(() => route.name === 'question-new')
</script>

<template>
  <div class="app-shell">
    <a class="skip-link" href="#main-content">跳到主要内容</a>

    <div class="app-frame">
      <AppTopBar />
      <main
        id="main-content"
        class="app-viewport"
        :class="{ 'app-viewport--workspace': isWorkspace }"
        tabindex="-1"
      >
        <RouterView />
      </main>
    </div>

    <nav class="mobile-nav" aria-label="快捷导航">
      <RouterLink
        v-for="item in mobileNavigation"
        :key="item.key"
        :to="item.to"
        :aria-current="activeKey === item.key ? 'page' : undefined"
      >
        <component :is="item.icon" class="mobile-nav__icon" aria-hidden="true" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  padding: var(--space-6) 0 var(--space-8);
  background: var(--color-bg);
}

.skip-link {
  position: fixed;
  top: var(--space-2);
  left: var(--space-2);
  z-index: 200;
  padding: 10px 14px;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-primary-active);
  font-size: var(--text-sm);
  transform: translateY(-160%);
}

.skip-link:focus {
  transform: translateY(0);
}

.app-frame {
  width: calc(100% - 64px);
  max-width: var(--layout-frame-max);
  margin: 0 auto;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-frame);
  background: var(--color-surface);
  box-shadow: var(--shadow-frame);
}

.app-viewport {
  padding: var(--space-7);
  border-radius: 0 0 var(--radius-frame) var(--radius-frame);
  background: var(--color-surface);
}

.app-viewport--workspace {
  background: var(--color-bg);
}

.app-viewport:focus {
  outline: none;
}

.mobile-nav {
  display: none;
}

@media (max-width: 767px) {
  .app-shell {
    padding: var(--space-4) 0 calc(var(--layout-bottom-nav-height) + var(--space-5));
  }

  .app-frame {
    width: calc(100% - 32px);
  }

  .app-viewport {
    padding: var(--space-4);
    border-radius: 0 0 8px 8px;
  }

  .mobile-nav {
    position: fixed;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: var(--z-mobile-nav);
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    padding: 5px 8px calc(5px + env(safe-area-inset-bottom));
    border-top: 1px solid var(--color-border-strong);
    background: var(--color-surface);
  }

  .mobile-nav a {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    min-height: 48px;
    border-radius: var(--radius-sm);
    color: var(--color-text-3);
    font-size: var(--text-sm);
    line-height: 20px;
  }

  .mobile-nav a:hover {
    background: var(--color-bg);
    color: var(--color-text-1);
  }

  .mobile-nav a[aria-current='page'] {
    color: var(--color-primary-active);
    font-weight: 650;
  }

  .mobile-nav__icon {
    width: var(--icon-md);
    height: var(--icon-md);
  }
}
</style>
