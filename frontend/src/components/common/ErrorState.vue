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
  <div class="error-state" role="alert">
    <a-result class="error-state__result" status="error" :title="title">
      <template #subtitle>
        <p class="error-state__message">{{ message }}</p>
        <p v-if="code" class="error-state__code">错误码：{{ code }}</p>
      </template>
      <template #extra>
        <div class="error-state__actions">
          <a-button v-if="showRetry" type="primary" @click="emit('retry')">
            {{ retryLabel }}
          </a-button>
          <slot />
        </div>
      </template>
    </a-result>
  </div>
</template>

<style scoped>
.error-state {
  display: flex;
  justify-content: center;
  padding: var(--space-6) var(--space-4);
}

.error-state__result {
  width: 100%;
  max-width: 520px;
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.error-state__message {
  max-width: 44ch;
  margin: 0 auto;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.error-state__code {
  margin-top: var(--space-1);
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
}

.error-state__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-2);
}
</style>
