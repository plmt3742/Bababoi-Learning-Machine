<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'list' | 'detail' | 'card'
    rows?: number
    label?: string
  }>(),
  {
    variant: 'list',
    rows: 3,
    label: '正在加载',
  },
)
</script>

<template>
  <div class="loading-skeleton" role="status" aria-live="polite" :aria-label="label">
    <span class="sr-only">{{ label }}…</span>

    <template v-if="variant === 'list'">
      <div v-for="row in rows" :key="row" class="skeleton-card">
        <div class="skeleton">
          <div class="sk sk--badge" />
          <div class="sk sk--long" />
          <div class="sk sk--medium" />
          <div class="sk sk--short" />
        </div>
      </div>
    </template>

    <template v-else-if="variant === 'detail'">
      <div class="skeleton-card skeleton-card--hero">
        <div class="skeleton">
          <div class="sk sk--badge" />
          <div class="sk sk--long" />
          <div class="sk sk--medium" />
          <div class="sk sk--short" />
        </div>
      </div>
      <div class="skeleton-card">
        <div class="skeleton">
          <div class="sk sk--badge" />
          <div class="sk sk--long" />
          <div class="sk sk--medium" />
        </div>
      </div>
      <div class="skeleton-card">
        <div class="skeleton">
          <div class="sk sk--badge" />
          <div class="sk sk--long" />
          <div class="sk sk--medium" />
        </div>
      </div>
    </template>

    <div v-else class="skeleton-card">
      <div class="skeleton">
        <div class="sk sk--badge" />
        <div class="sk sk--long" />
        <div class="sk sk--medium" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.loading-skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.skeleton-card {
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.skeleton-card--hero {
  padding: var(--space-6);
}

.skeleton {
  display: flex;
  flex-direction: column;
  gap: 9px;
  width: 100%;
  padding: 2px 0 4px;
}

.sk {
  height: 12px;
  border-radius: 3px;
  background: var(--color-page-deep);
  animation: calm-skeleton-pulse 1.8s ease-in-out infinite;
}

.sk--badge {
  width: 52px;
  height: 24px;
}

.sk--long {
  width: 100%;
  height: 16px;
}

.sk--medium {
  width: 76%;
}

.sk--short {
  width: 42%;
}

.sk:nth-child(3) {
  animation-delay: 0.15s;
}

.sk:nth-child(4) {
  animation-delay: 0.3s;
}

@keyframes calm-skeleton-pulse {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.45;
  }
}
</style>
