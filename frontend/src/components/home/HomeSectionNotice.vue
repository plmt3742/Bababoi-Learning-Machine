<script setup lang="ts">
import { RouterLink } from 'vue-router'

withDefaults(
  defineProps<{
    title: string
    message?: string
    tone?: 'error' | 'empty'
    actionLabel?: string
    actionTo?: string
  }>(),
  {
    message: '',
    tone: 'empty',
    actionLabel: '',
    actionTo: '',
  },
)

const emit = defineEmits<{ action: [] }>()
</script>

<template>
  <div class="notice" :class="`notice--${tone}`" :role="tone === 'error' ? 'status' : undefined">
    <div class="notice__body">
      <p class="notice__title">{{ title }}</p>
      <p v-if="message" class="notice__message">{{ message }}</p>
    </div>

    <RouterLink v-if="actionLabel && actionTo" class="btn btn--outline btn--sm" :to="actionTo">
      {{ actionLabel }}
    </RouterLink>
    <button
      v-else-if="actionLabel"
      class="btn btn--quiet btn--sm"
      type="button"
      @click="emit('action')"
    >
      {{ actionLabel }}
    </button>
  </div>
</template>

<style scoped>
.notice {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-2) var(--space-4);
  padding: var(--space-5) var(--space-6);
}

.notice--error {
  margin: var(--space-4) var(--space-6);
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-warning-border);
  border-radius: var(--radius-md);
  background: var(--color-warning-soft);
}

.notice__body {
  min-width: 0;
}

.notice__title {
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 650;
}

.notice--error .notice__title {
  color: var(--color-warning-text);
}

.notice__message {
  max-width: 58ch;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  overflow-wrap: anywhere;
}

.notice .btn {
  flex: none;
}

@media (max-width: 767px) {
  .notice {
    align-items: flex-start;
    padding: var(--space-4);
  }

  .notice--error {
    margin: var(--space-3) var(--space-4);
    padding: var(--space-3);
  }

  .notice .btn {
    width: 100%;
  }
}
</style>
