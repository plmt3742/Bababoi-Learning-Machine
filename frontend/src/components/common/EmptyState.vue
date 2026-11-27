<script setup lang="ts">
import Mascot3D from './Mascot3D.vue'

withDefaults(
  defineProps<{
    title?: string
    description?: string
    actionLabel?: string
    compact?: boolean
  }>(),
  {
    title: '暂无数据',
    description: '',
    actionLabel: '',
    compact: false,
  },
)

const emit = defineEmits<{ action: [] }>()
</script>

<template>
  <div class="state-card" :class="{ 'state-card--compact': compact }">
    <div class="state-illustration" aria-hidden="true">
      <slot name="image">
        <Mascot3D :size="32" state="default" />
      </slot>
    </div>
    <h3>{{ title }}</h3>
    <p v-if="description">{{ description }}</p>
    <button
      v-if="actionLabel"
      class="btn btn--outline btn--sm"
      type="button"
      @click="emit('action')"
    >
      {{ actionLabel }}
    </button>
    <slot />
  </div>
</template>

<style scoped>
.state-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 9px;
  min-height: var(--layout-empty-min-height);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.state-card--compact {
  min-height: 0;
  padding: var(--space-4);
}

.state-illustration {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  margin: 2px 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text-3);
}

.state-illustration :deep(svg),
.state-illustration > svg {
  width: 22px;
  height: 22px;
}

.state-card h3 {
  font-size: var(--text-base);
  line-height: 24px;
  font-weight: 650;
}

.state-card > p {
  max-width: 46ch;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.state-card .btn {
  margin-top: auto;
}
</style>
