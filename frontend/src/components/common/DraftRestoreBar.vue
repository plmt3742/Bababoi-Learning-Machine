<script setup lang="ts">
import { computed, ref } from 'vue'
import { formatDraftClockTime } from '../../utils/draft'

const props = defineProps<{
  updatedAt: string
  source: 'local' | 'server'
}>()

const emit = defineEmits<{
  restore: []
  discard: []
  later: []
}>()

const rootRef = ref<HTMLElement | null>(null)
const restoreButtonRef = ref<HTMLButtonElement | null>(null)

const timeLabel = computed(() => {
  const time = formatDraftClockTime(props.updatedAt)
  const source = props.source === 'server' ? '服务端' : '本地'
  return time ? `${source}保存于 ${time}` : `${source}有未完成草稿`
})

defineExpose({
  focusRestore(): void {
    restoreButtonRef.value?.focus()
  },
  focusRoot(): void {
    rootRef.value?.focus()
  },
})
</script>

<template>
  <section
    ref="rootRef"
    class="draft-restore"
    tabindex="-1"
    role="region"
    aria-labelledby="draft-restore-title"
    @keydown.esc.stop.prevent="emit('later')"
  >
    <div class="draft-restore__body">
      <p id="draft-restore-title" class="draft-restore__title">发现未完成的草稿</p>
      <p class="draft-restore__meta">{{ timeLabel }} · 恢复不会覆盖当前输入，直到你确认</p>
    </div>

    <div class="draft-restore__actions">
      <button
        ref="restoreButtonRef"
        class="btn btn--primary btn--sm"
        type="button"
        @click="emit('restore')"
      >
        恢复
      </button>
      <button class="btn btn--outline btn--sm" type="button" @click="emit('later')">稍后</button>
      <button
        class="btn btn--quiet btn--sm draft-restore__discard"
        type="button"
        @click="emit('discard')"
      >
        丢弃
      </button>
    </div>
  </section>
</template>

<style scoped>
.draft-restore {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding: 11px var(--space-4);
  border: 1px solid var(--color-warning-border);
  border-radius: var(--radius-lg);
  background: var(--color-warning-soft);
}

.draft-restore__body {
  min-width: 0;
}

.draft-restore__title {
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 650;
}

.draft-restore__meta {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  overflow-wrap: anywhere;
}

.draft-restore__actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.draft-restore__discard {
  color: var(--color-danger-text);
}

.draft-restore__discard:hover {
  background: var(--color-danger-soft);
  color: var(--color-danger-text-hover);
}

@media (max-width: 560px) {
  .draft-restore {
    align-items: stretch;
    flex-direction: column;
    padding: var(--space-3);
  }

  .draft-restore__actions .btn {
    flex: 0 0 auto;
  }
}
</style>
