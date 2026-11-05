<script setup lang="ts">
import { RouterLink } from 'vue-router'
import AppNavigation from './AppNavigation.vue'

defineProps<{ inDrawer?: boolean }>()

const emit = defineEmits<{ navigate: [] }>()
</script>

<template>
  <div class="app-sidebar" :class="{ 'app-sidebar--drawer': inDrawer }">
    <RouterLink
      class="app-sidebar__brand"
      to="/"
      aria-label="Bababoi Learning Machine 首页"
      @click="emit('navigate')"
    >
      <span class="app-sidebar__mark" aria-hidden="true">
        <svg viewBox="0 0 24 24">
          <path
            d="M7 5.5h6.5a3 3 0 0 1 0 6H7m0 0h7.5a3 3 0 0 1 0 6H7"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </span>
      <span class="app-sidebar__wordmark">
        <span class="app-sidebar__name">Bababoi</span>
        <span class="app-sidebar__tagline">Learning Machine</span>
      </span>
    </RouterLink>

    <div class="app-sidebar__nav">
      <AppNavigation @navigate="emit('navigate')" />
    </div>
  </div>
</template>

<style scoped>
.app-sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  height: 100%;
  padding: var(--space-5) var(--space-3) var(--space-4);
  background: var(--color-surface);
}

.app-sidebar--drawer {
  padding-top: var(--space-4);
}

.app-sidebar__brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0 var(--space-2);
  color: var(--color-text-1);
}

.app-sidebar__brand:hover {
  color: var(--color-text-1);
}

.app-sidebar__mark {
  display: grid;
  flex: none;
  width: var(--layout-brand-mark);
  height: var(--layout-brand-mark);
  place-items: center;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: var(--color-surface);
}

.app-sidebar__mark svg {
  width: var(--icon-lg);
  height: var(--icon-lg);
}

.app-sidebar__wordmark {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.app-sidebar__name {
  font-size: var(--text-base);
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: -0.01em;
}

.app-sidebar__tagline {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: 1.35;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.app-sidebar__nav {
  flex: 1;
  min-height: 0;
}
</style>
