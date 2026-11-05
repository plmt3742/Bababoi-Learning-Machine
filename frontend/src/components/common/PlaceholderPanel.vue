<script setup lang="ts">
import { IconFormula } from '@arco-design/web-vue/es/icon'

defineProps<{
  hint: string
  task: string
}>()
</script>

<template>
  <a-card class="placeholder-panel" :bordered="false">
    <div class="placeholder-panel__body">
      <a-empty description="页面骨架已就位">
        <template #image>
          <span class="placeholder-panel__glyph" aria-hidden="true">
            <IconFormula />
          </span>
        </template>
      </a-empty>
      <p class="placeholder-panel__hint">{{ hint }}</p>
      <a-tag color="gray" size="small">{{ task }}</a-tag>
    </div>
  </a-card>
</template>

<style scoped>
.placeholder-panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
}

.placeholder-panel :deep(.arco-card-body) {
  padding: 0;
}

.placeholder-panel__body {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  min-height: var(--layout-empty-min-height);
  padding: var(--space-7) var(--space-5);
  text-align: center;
}

.placeholder-panel__glyph {
  display: grid;
  width: var(--layout-empty-glyph);
  height: var(--layout-empty-glyph);
  margin: 0 auto;
  place-items: center;
  border-radius: var(--radius-lg);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: var(--text-3xl);
}

.placeholder-panel :deep(.arco-empty-description) {
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.placeholder-panel__hint {
  max-width: 52ch;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: balance;
}
</style>
