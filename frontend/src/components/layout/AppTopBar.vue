<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { IconMenu } from '@arco-design/web-vue/es/icon'

const emit = defineEmits<{ openMenu: [] }>()
const route = useRoute()

const pageTitle = computed(() => route.meta.title)
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

    <a-tag class="app-topbar__stage" color="arcoblue" size="small">M0 骨架</a-tag>
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
  flex-direction: column;
  min-width: 0;
}

.app-topbar__product {
  color: var(--color-text-3);
  font-size: var(--text-xs);
  line-height: 1.35;
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

.app-topbar__stage {
  margin-left: auto;
  flex: none;
}

@media (max-width: 1199px) {
  .app-topbar__menu {
    display: inline-flex;
  }
}

@media (max-width: 767px) {
  .app-topbar {
    padding: 0 var(--space-2);
  }

  .app-topbar__product {
    display: none;
  }
}
</style>
