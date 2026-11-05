<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { navigationItems } from './navigation'

const emit = defineEmits<{ navigate: [] }>()
const route = useRoute()

const activeKey = computed(() => route.meta.navKey)

function handleNavigate() {
  emit('navigate')
}
</script>

<template>
  <nav class="app-nav" aria-label="主导航">
    <ul class="app-nav__list">
      <li v-for="item in navigationItems" :key="item.key" class="app-nav__item">
        <RouterLink
          v-if="item.to"
          :to="item.to"
          class="app-nav__link"
          :class="{ 'app-nav__link--active': activeKey === item.key }"
          :aria-current="activeKey === item.key ? 'page' : undefined"
          @click="handleNavigate"
        >
          <component :is="item.icon" class="app-nav__icon" aria-hidden="true" />
          <span class="app-nav__label">{{ item.label }}</span>
          <a-tag v-if="item.badge" class="app-nav__badge" color="gray" size="small">
            {{ item.badge }}
          </a-tag>
        </RouterLink>
        <span
          v-else
          class="app-nav__link app-nav__link--disabled"
          aria-disabled="true"
          :title="`${item.label}将在 P1 提供`"
        >
          <component :is="item.icon" class="app-nav__icon" aria-hidden="true" />
          <span class="app-nav__label">{{ item.label }}</span>
          <a-tag v-if="item.badge" class="app-nav__badge" color="gray" size="small">
            {{ item.badge }}
          </a-tag>
        </span>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.app-nav__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.app-nav__link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: var(--control-height);
  padding: 0 var(--space-3);
  border-radius: var(--radius-md);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  font-weight: 500;
  line-height: var(--text-sm-leading);
}

.app-nav__link:hover {
  background: var(--color-fill);
  color: var(--color-text-1);
}

.app-nav__link--active,
.app-nav__link--active:hover {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: 600;
}

.app-nav__link--disabled,
.app-nav__link--disabled:hover {
  background: transparent;
  color: var(--color-text-3);
  cursor: not-allowed;
}

.app-nav__icon {
  width: var(--icon-sm);
  height: var(--icon-sm);
  flex: none;
}

.app-nav__label {
  flex: 1;
  min-width: 0;
}

.app-nav__badge {
  margin-left: auto;
}
</style>
