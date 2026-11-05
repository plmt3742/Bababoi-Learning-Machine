<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string
    message?: string
    retryLabel?: string
    showRetry?: boolean
    code?: string
  }>(),
  {
    title: '加载失败',
    message: '请求没有成功，请检查网络后重试。',
    retryLabel: '重试',
    showRetry: true,
    code: '',
  },
)

const emit = defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="state-card state-card--error" role="alert">
    <div class="state-illustration state-illustration--error" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v6M12 17h.01" />
      </svg>
    </div>
    <h3>{{ title }}</h3>
    <p>{{ message }}</p>
    <p v-if="code" class="error-code">{{ code }}</p>
    <div class="state-card__actions">
      <button v-if="showRetry" class="btn btn--danger btn--sm" type="button" @click="emit('retry')">
        {{ retryLabel }}
      </button>
      <slot />
    </div>
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

.state-illustration--error {
  border-color: var(--color-danger-border);
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.state-illustration svg {
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

.error-code {
  color: var(--color-danger-text);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 20px;
}

.state-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: auto;
}
</style>
