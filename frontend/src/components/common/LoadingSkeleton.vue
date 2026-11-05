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
    <span class="loading-skeleton__sr-only">{{ label }}…</span>

    <template v-if="variant === 'list'">
      <div v-for="row in rows" :key="row" class="loading-skeleton__card">
        <a-skeleton :animation="true">
          <a-skeleton-line
            :rows="3"
            :widths="['34%', '100%', '58%']"
            :line-height="12"
            :line-spacing="12"
          />
        </a-skeleton>
      </div>
    </template>

    <template v-else-if="variant === 'detail'">
      <div class="loading-skeleton__card loading-skeleton__card--hero">
        <a-skeleton :animation="true">
          <a-skeleton-line
            :rows="5"
            :widths="['28%', '92%', '100%', '76%', '42%']"
            :line-height="14"
            :line-spacing="14"
          />
        </a-skeleton>
      </div>
      <div class="loading-skeleton__card">
        <a-skeleton :animation="true">
          <a-skeleton-line
            :rows="4"
            :widths="['24%', '100%', '84%', '64%']"
            :line-height="12"
            :line-spacing="12"
          />
        </a-skeleton>
      </div>
      <div class="loading-skeleton__card">
        <a-skeleton :animation="true">
          <a-skeleton-line
            :rows="3"
            :widths="['22%', '96%', '58%']"
            :line-height="12"
            :line-spacing="12"
          />
        </a-skeleton>
      </div>
    </template>

    <div v-else class="loading-skeleton__card">
      <a-skeleton :animation="true">
        <a-skeleton-line
          :rows="4"
          :widths="['30%', '100%', '88%', '52%']"
          :line-height="12"
          :line-spacing="12"
        />
      </a-skeleton>
    </div>
  </div>
</template>

<style scoped>
.loading-skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.loading-skeleton__sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  padding: 0;
  border: 0;
  margin: -1px;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

.loading-skeleton__card {
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.loading-skeleton__card--hero {
  padding: var(--space-6);
}

.loading-skeleton :deep(.arco-skeleton-line-row) {
  background: var(--color-fill);
}
</style>
