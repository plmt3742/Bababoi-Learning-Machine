<script setup lang="ts">
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
  <div class="empty-state" :class="{ 'empty-state--compact': compact }">
    <a-empty class="empty-state__empty">
      <template v-if="$slots.image" #image>
        <slot name="image" />
      </template>
      <div class="empty-state__copy">
        <p class="empty-state__title">{{ title }}</p>
        <p v-if="description" class="empty-state__description">{{ description }}</p>
      </div>
    </a-empty>

    <div v-if="actionLabel || $slots.default" class="empty-state__actions">
      <a-button v-if="actionLabel" type="primary" @click="emit('action')">
        {{ actionLabel }}
      </a-button>
      <slot />
    </div>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  min-height: var(--layout-empty-min-height);
  padding: var(--space-6) var(--space-4);
}

.empty-state__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.empty-state__copy {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  align-items: center;
  text-align: center;
}

.empty-state__title {
  color: var(--color-text-1);
  font-size: var(--text-base);
  font-weight: 600;
  line-height: var(--text-base-leading);
}

.empty-state__description {
  max-width: 46ch;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.empty-state__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-2);
}

.empty-state--compact {
  min-height: 0;
  padding: var(--space-4);
  border-radius: var(--radius-md);
  background: var(--color-fill);
}

.empty-state--compact :deep(.arco-empty-image) {
  display: none;
}

.empty-state--compact :deep(.arco-empty-description) {
  margin-top: 0;
}
</style>
