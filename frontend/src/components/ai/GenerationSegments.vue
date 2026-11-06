<script setup lang="ts">
import { computed } from 'vue'
import type { Component } from 'vue'
import {
  IconArrowRight,
  IconCheck,
  IconClockCircle,
  IconClose,
  IconLoading,
  IconMinus,
  IconRefresh,
} from '@arco-design/web-vue/es/icon'
import type { Task } from '../../api/types'
import { latestTask } from '../../utils/task'
import {
  SEGMENT_INDEXES,
  latestSegmentTask,
  segmentGroupStatusLabel,
  summarizeSegments,
} from '../../utils/segments'
import SegmentCard from './SegmentCard.vue'

type AnalysisState = 'waiting' | 'queued' | 'running' | 'done' | 'failed'

const props = withDefaults(
  defineProps<{
    tasks: Task[]
    polling?: boolean
    loading?: boolean
    timedOut?: boolean
    stopped?: boolean
    errorMessage?: string
    errorCode?: string
    generatedCount?: number
    analysisReady?: boolean
    generationRequested?: boolean
    retryingTaskId?: number | null
  }>(),
  {
    polling: false,
    loading: false,
    timedOut: false,
    stopped: false,
    errorMessage: '',
    errorCode: '',
    generatedCount: 0,
    analysisReady: false,
    generationRequested: false,
    retryingTaskId: null,
  },
)

const emit = defineEmits<{
  retry: [taskId: number]
  stop: []
  refresh: []
  generate: []
  practice: []
}>()

const analysisTask = computed(() => latestTask(props.tasks, 'analysis'))
const segmentSummary = computed(() => summarizeSegments(props.tasks))
const segmentSlots = computed(() =>
  SEGMENT_INDEXES.map((index) => ({ index, task: latestSegmentTask(props.tasks, index) })),
)

const analysisState = computed<AnalysisState>(() => {
  const task = analysisTask.value

  if (props.analysisReady) {
    if (task?.status === 'queued' || task?.status === 'running') return task.status
    return 'done'
  }

  if (!task) return 'waiting'
  if (task.status === 'failed') return 'failed'
  if (task.status === 'queued' || task.status === 'running') return task.status
  return 'done'
})

const analysisFailed = computed(
  () => analysisState.value === 'failed' && analysisTask.value !== null,
)
const analysisMeta = computed(() => {
  const task = analysisTask.value

  switch (analysisState.value) {
    case 'queued':
      return '排队中，等待开始'
    case 'running':
      return '正在提取考点与错误原因'
    case 'done':
      return props.analysisReady ? '分析结果已就绪' : '分析完成，正在同步结果'
    case 'failed':
      return task?.error_code ? `失败 · ${task.error_code}` : '分析没有成功完成'
    default:
      return '等待任务开始'
  }
})

const generationActive = computed(
  () => segmentSummary.value.activeCount > 0 || props.generationRequested,
)
const syncPending = computed(
  () => segmentSummary.value.status === 'done' && props.generatedCount === 0,
)
const generationPending = computed(() => generationActive.value || syncPending.value)
const canPractice = computed(() => props.generatedCount > 0)
const showRefreshAction = computed(
  () =>
    !props.polling &&
    (segmentSummary.value.activeCount > 0 ||
      props.timedOut ||
      props.stopped ||
      Boolean(props.errorMessage)),
)

const overallTag = computed<{ label: string; className: string; tone: 'done' | 'run' | 'fail' }>(
  () => {
    if (props.timedOut || props.stopped) {
      return { label: '已暂停', className: 'tag--draft', tone: 'run' }
    }
    if (analysisFailed.value) {
      return { label: '需要处理', className: 'tag--fail', tone: 'fail' }
    }
    if (
      props.polling ||
      generationPending.value ||
      segmentSummary.value.status === 'running' ||
      segmentSummary.value.status === 'queued'
    ) {
      return { label: '进行中', className: 'tag--run', tone: 'run' }
    }
    if (segmentSummary.value.status === 'done') {
      return { label: '已完成', className: 'tag--ok', tone: 'done' }
    }
    if (segmentSummary.value.status === 'partial-failed') {
      return {
        label: segmentGroupStatusLabel('partial-failed'),
        className: 'tag--draft',
        tone: 'run',
      }
    }
    if (segmentSummary.value.status === 'failed') {
      return { label: segmentGroupStatusLabel('failed'), className: 'tag--fail', tone: 'fail' }
    }
    return { label: '等待中', className: '', tone: 'run' }
  },
)

const progressNote = computed(() => {
  if (props.timedOut) {
    return '等待超过 2 分钟，已暂停自动刷新；服务器任务可能仍在继续，可点击「刷新一次」查看最新状态。'
  }
  if (props.stopped) {
    return '已暂停自动刷新；服务器任务仍在继续，可点击「刷新一次」查看最新状态。'
  }
  if (props.polling || generationActive.value) {
    return '3 段并发生成，每 1.5 秒自动刷新；单段失败不影响其余两段，可单独重试。'
  }
  if (segmentSummary.value.failedCount > 0) {
    return '生成已结束，失败段可单独重试；其余段的结果会保留。'
  }
  if (segmentSummary.value.status === 'done') {
    return '3 段均已完成，可去练习或整组重新生成。'
  }
  return '生成相似题后，3 段任务会各自更新状态；失败段可单独重试。'
})

function analysisIcon(state: AnalysisState): Component {
  switch (state) {
    case 'done':
      return IconCheck
    case 'failed':
      return IconClose
    case 'queued':
      return IconClockCircle
    case 'running':
      return IconLoading
    default:
      return IconMinus
  }
}

function handleRetry(taskId: number): void {
  emit('retry', taskId)
}

function retryAnalysis(): void {
  if (analysisTask.value) emit('retry', analysisTask.value.id)
}
</script>

<template>
  <section class="segments-card" aria-labelledby="segments-progress-title">
    <div class="segments-card__head">
      <h2 id="segments-progress-title">处理进度</h2>
      <span class="tag" :class="overallTag.className">
        <svg
          v-if="overallTag.tone === 'done'"
          class="icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="m5 12 4 4L19 6" />
        </svg>
        <svg
          v-else-if="overallTag.tone === 'fail'"
          class="icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="m6 6 12 12M18 6 6 18" />
        </svg>
        <span v-else-if="overallTag.className === 'tag--run'" class="dot" aria-hidden="true" />
        {{ overallTag.label }}
      </span>
    </div>

    <div class="analysis-row" :class="`analysis-row--${analysisState}`">
      <span
        class="analysis-row__mark"
        :class="`analysis-row__mark--${analysisState}`"
        aria-hidden="true"
      >
        <component
          :is="analysisIcon(analysisState)"
          class="icon"
          :class="{ 'analysis-row__icon--spin': analysisState === 'running' }"
        />
      </span>
      <div class="analysis-row__body">
        <span class="analysis-row__title">AI 分析</span>
        <span class="analysis-row__meta">{{ analysisMeta }}</span>
      </div>
      <button
        v-if="analysisFailed && analysisTask"
        class="btn btn--quiet btn--sm analysis-row__retry"
        type="button"
        :disabled="retryingTaskId !== null"
        @click="retryAnalysis"
      >
        {{ retryingTaskId === analysisTask.id ? '重试中…' : '重试' }}
      </button>
    </div>

    <div class="segments-head">
      <h3>相似题 · 3 段并发</h3>
      <span class="segments-head__count">{{ segmentSummary.doneCount }} / 3 段完成</span>
    </div>

    <div class="segment-stack">
      <SegmentCard
        v-for="slot in segmentSlots"
        :key="slot.index"
        :index="slot.index"
        :task="slot.task"
        :requested="generationRequested"
        :retrying="retryingTaskId === slot.task?.id"
        :retry-disabled="retryingTaskId !== null"
        @retry="handleRetry"
      />
    </div>

    <div v-if="errorMessage" class="segments-error" role="alert">
      <p class="segments-error__title">
        进度刷新失败
        <span v-if="errorCode" class="segments-error__code">{{ errorCode }}</span>
      </p>
      <p class="segments-error__text">{{ errorMessage }}</p>
      <button class="btn btn--quiet btn--sm" type="button" @click="emit('refresh')">
        重试刷新
      </button>
    </div>

    <p class="segments-note">{{ progressNote }}</p>

    <p class="segments-count">
      已生成 <strong>{{ generatedCount }}</strong> / 3 道相似题
    </p>

    <div class="segments-cta">
      <button
        v-if="canPractice"
        class="btn btn--primary btn--block"
        type="button"
        @click="emit('practice')"
      >
        去练习 · {{ generatedCount }} 道相似题
        <IconArrowRight class="icon" />
      </button>
      <button
        v-else-if="generationPending"
        class="btn btn--primary btn--block"
        type="button"
        disabled
      >
        生成中…
      </button>
      <button
        v-else-if="analysisFailed"
        class="btn btn--danger btn--block"
        type="button"
        :disabled="retryingTaskId !== null"
        @click="retryAnalysis"
      >
        重试 AI 分析
      </button>
      <button
        v-else
        class="btn btn--primary btn--block"
        type="button"
        :disabled="!analysisReady"
        :title="analysisReady ? undefined : 'AI 分析完成后即可生成相似题'"
        @click="emit('generate')"
      >
        {{ segmentSummary.failedCount > 0 ? '重新生成 3 题' : '生成 3 道相似题' }}
      </button>
      <button
        v-if="canPractice && !generationActive"
        class="btn btn--quiet btn--sm segments-cta__regen"
        type="button"
        @click="emit('generate')"
      >
        重新生成整组
      </button>
    </div>

    <div v-if="polling || showRefreshAction" class="segments-subactions">
      <button v-if="polling" class="btn btn--quiet btn--sm" type="button" @click="emit('stop')">
        暂停自动刷新
      </button>
      <button
        v-else
        class="btn btn--quiet btn--sm"
        type="button"
        :disabled="loading"
        @click="emit('refresh')"
      >
        <IconRefresh class="icon" />
        刷新一次
      </button>
    </div>
  </section>
</template>

<style scoped>
.segments-card {
  padding: 17px var(--space-5) var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.segments-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.segments-card__head h2 {
  font-size: var(--text-base);
  line-height: 24px;
  font-weight: 650;
}

.segments-card__head .tag {
  flex: none;
}

.analysis-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: var(--space-4);
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
}

.analysis-row--failed {
  border-color: var(--color-danger-border);
  background: var(--color-danger-soft);
}

.analysis-row__mark {
  display: grid;
  place-items: center;
  flex: none;
  width: 22px;
  height: 22px;
  border: 1px solid var(--color-border-strong);
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-text-3);
}

.analysis-row__mark .icon {
  width: 12px;
  height: 12px;
}

.analysis-row__mark--done {
  border-color: var(--color-success-border);
  background: var(--color-success-soft);
  color: var(--color-success);
}

.analysis-row__mark--queued,
.analysis-row__mark--running {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary-active);
}

.analysis-row__mark--failed {
  border-color: var(--color-danger-border);
  background: var(--color-surface);
  color: var(--color-danger);
}

.analysis-row__icon--spin {
  animation: segment-spin 1s linear infinite;
}

.analysis-row__body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.analysis-row__title {
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 650;
}

.analysis-row__meta {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  overflow-wrap: anywhere;
}

.analysis-row__retry {
  flex: none;
  min-height: 30px;
  margin: -4px -6px -4px auto;
}

.segments-head {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4px 10px;
  margin-top: var(--space-5);
  margin-bottom: 8px;
}

.segments-head h3 {
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 650;
}

.segments-head__count {
  margin-left: auto;
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.segment-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.segments-error {
  margin-top: var(--space-4);
  padding: 10px var(--space-3);
  border: 1px solid var(--color-danger-border);
  border-radius: var(--radius-md);
  background: var(--color-danger-soft);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.segments-error__title {
  color: var(--color-text-1);
  font-weight: 600;
}

.segments-error__code {
  margin-left: 2px;
  color: var(--color-danger-text);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 400;
}

.segments-error__text {
  margin-top: 2px;
  text-wrap: pretty;
}

.segments-error .btn {
  margin-top: var(--space-1);
  margin-left: calc(var(--space-2) * -1);
}

.segments-note {
  margin-top: var(--space-4);
  padding: 10px var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.segments-count {
  margin-top: var(--space-4);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.segments-count strong {
  color: var(--color-text-1);
  font-weight: 650;
}

.segments-cta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 10px;
}

.segments-cta .btn--block {
  min-height: 44px;
}

.segments-cta__regen {
  align-self: center;
  min-height: 32px;
}

.segments-subactions {
  display: flex;
  justify-content: center;
  margin-top: var(--space-2);
}

.segments-subactions .btn {
  min-height: 32px;
}

@keyframes segment-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .analysis-row__icon--spin {
    animation: none;
  }
}

@media (max-width: 767px) {
  .segments-card {
    padding: 15px var(--space-4) var(--space-4);
  }
}
</style>
