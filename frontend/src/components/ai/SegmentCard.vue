<script setup lang="ts">
import { computed } from 'vue'
import type { GenerationTargetIndex, Task } from '../../api/types'
import { difficultyLabel } from '../../utils/question'
import { segmentDifficulty, segmentStatusLabel, type SegmentStatus } from '../../utils/segments'
import { taskFailureMessage } from '../../utils/task'

const props = withDefaults(
  defineProps<{
    index: GenerationTargetIndex
    task?: Task | null
    requested?: boolean
    retrying?: boolean
    retryDisabled?: boolean
    compact?: boolean
  }>(),
  {
    task: null,
    requested: false,
    retrying: false,
    retryDisabled: false,
    compact: false,
  },
)

const emit = defineEmits<{ retry: [taskId: number] }>()

const number = computed(() => String(props.index).padStart(2, '0'))
const difficultyText = computed(() => difficultyLabel(segmentDifficulty(props.task, props.index)))
const status = computed<SegmentStatus>(() => {
  if (props.task) return props.task.status
  return props.requested ? 'queued' : 'waiting'
})
const statusText = computed(() => segmentStatusLabel(status.value))
const statusClass = computed(() => {
  switch (status.value) {
    case 'done':
      return 'tag tag--ok'
    case 'failed':
      return 'tag tag--fail'
    case 'running':
      return 'tag tag--run'
    case 'waiting':
      return 'tag tag--point'
    default:
      return 'tag'
  }
})
const errorText = computed(() => {
  if (!props.task || props.task.status !== 'failed') return ''
  return taskFailureMessage(props.task)
})
const metaText = computed(() => {
  const task = props.task
  if (!task) return props.requested ? '正在提交任务' : '尚未生成'

  const retry = task.retry_index > 0 ? ` · 第 ${task.retry_index + 1} 次尝试` : ''
  return `任务 #${task.id}${retry}`
})

function handleRetry(): void {
  if (props.task) emit('retry', props.task.id)
}
</script>

<template>
  <article
    class="segment"
    :class="[`segment--${status}`, { 'segment--compact': compact }]"
    :aria-label="`第 ${number} 段，${difficultyText}`"
  >
    <div class="segment__head">
      <span class="segment__no" aria-hidden="true">{{ number }}</span>
      <span class="tag segment__difficulty">{{ difficultyText }}</span>
      <span class="segment__status" :class="statusClass">
        <span v-if="status === 'running'" class="dot" aria-hidden="true" />
        {{ statusText }}
      </span>
    </div>

    <p v-if="errorText" class="segment__error">
      <code v-if="task?.error_code" class="segment__error-code">{{ task.error_code }}</code>
      <span>{{ errorText }}</span>
    </p>

    <div class="segment__foot">
      <span class="segment__meta">{{ metaText }}</span>
      <button
        v-if="status === 'failed'"
        class="btn btn--quiet btn--sm segment__retry"
        type="button"
        :disabled="retrying || retryDisabled"
        :aria-busy="retrying"
        @click="handleRetry"
      >
        {{ retrying ? '重试中…' : '重试该段' }}
      </button>
    </div>
  </article>
</template>

<style scoped>
.segment {
  min-width: 0;
  padding: 12px 14px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.segment--compact {
  padding: 10px 12px 8px;
}

.segment--waiting {
  border-style: dashed;
  background: var(--color-surface-subtle);
}

.segment--running {
  border-color: var(--color-primary-border);
}

.segment--failed {
  border-color: var(--color-danger-border);
  background: var(--color-danger-soft);
}

.segment__head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}

.segment__no {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 650;
  letter-spacing: 0.08em;
  line-height: 1;
}

.segment__difficulty {
  height: 24px;
  padding: 0 7px;
  color: var(--color-text-2);
}

.segment__status {
  margin-left: auto;
}

.segment__error {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 2px 6px;
  margin-top: 8px;
  padding: 7px 9px;
  border: 1px solid var(--color-danger-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  overflow-wrap: anywhere;
}

.segment__error-code {
  color: var(--color-danger-text);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 600;
}

.segment__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 4px 8px;
  margin-top: 9px;
  padding-top: 7px;
  border-top: 1px solid var(--color-border);
}

.segment__meta {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  overflow-wrap: anywhere;
}

.segment__retry {
  min-height: 30px;
  margin-right: -8px;
  padding: 0 8px;
}
</style>
