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
import { hasActiveTasks, latestTask, taskErrorMessage, taskStageLabel } from '../../utils/task'

type StepState = 'waiting' | 'queued' | 'running' | 'done' | 'failed'

interface StepView {
  key: 'analysis' | 'quiz' | 'validation'
  title: string
  state: StepState
  meta: string
}

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
const quizTask = computed(() => latestTask(props.tasks, 'quiz'))
const hasActiveTask = computed(() => hasActiveTasks(props.tasks))

const analysisState = computed<StepState>(() => {
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

const quizState = computed<StepState>(() => {
  const task = quizTask.value

  if (task) {
    if (task.status === 'failed') return 'failed'
    if (task.status === 'queued' || task.status === 'running') return task.status
    return 'done'
  }

  if (props.generationRequested) return 'queued'
  if (props.generatedCount > 0) return 'done'
  return 'waiting'
})

const validationState = computed<StepState>(() => {
  switch (quizState.value) {
    case 'running':
      return 'running'
    case 'queued':
      return 'queued'
    case 'done':
      return 'done'
    case 'failed':
    case 'waiting':
      return 'waiting'
    default:
      return 'waiting'
  }
})

const blockingFailedTasks = computed<Task[]>(() => {
  const failed: Task[] = []

  if (analysisState.value === 'failed' && analysisTask.value) failed.push(analysisTask.value)
  if (quizState.value === 'failed' && quizTask.value) failed.push(quizTask.value)

  return failed
})

const hasFailure = computed(() => blockingFailedTasks.value.length > 0)
const primaryFailure = computed(() => blockingFailedTasks.value[0] ?? null)
const hasActiveProgress = computed(
  () =>
    analysisState.value === 'queued' ||
    analysisState.value === 'running' ||
    quizState.value === 'queued' ||
    quizState.value === 'running',
)
const syncPending = computed(
  () =>
    (analysisState.value === 'done' && !props.analysisReady) ||
    (quizState.value === 'done' && props.generatedCount === 0),
)
const generationActive = computed(
  () => quizState.value === 'queued' || quizState.value === 'running' || props.generationRequested,
)
const generationPending = computed(() => generationActive.value || syncPending.value)
const hasFinishedTask = computed(
  () => analysisState.value === 'done' || quizState.value === 'done' || props.generatedCount > 0,
)
const showRefreshAction = computed(
  () =>
    !props.polling &&
    (hasActiveTask.value || props.timedOut || props.stopped || Boolean(props.errorMessage)),
)

function formatClock(value: string | null | undefined): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''

  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date)
}

function formatDuration(
  start: string | null | undefined,
  finish: string | null | undefined,
): string {
  if (!start || !finish) return ''
  const startTime = new Date(start).getTime()
  const finishTime = new Date(finish).getTime()
  if (!Number.isFinite(startTime) || !Number.isFinite(finishTime)) return ''

  const seconds = Math.max(1, Math.round((finishTime - startTime) / 1000))
  if (seconds < 60) return `${seconds} 秒`

  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60
  return remainder > 0 ? `${minutes} 分 ${remainder} 秒` : `${minutes} 分`
}

function taskClock(task: Task | null): string {
  if (!task) return ''
  return formatClock(task.started_at ?? task.created_at)
}

function taskDuration(task: Task | null): string {
  if (!task) return ''
  return formatDuration(task.started_at ?? task.created_at, task.finished_at)
}

const analysisMeta = computed(() => {
  const task = analysisTask.value
  const time = taskClock(task)
  const duration = taskDuration(task)

  switch (analysisState.value) {
    case 'queued':
      return '排队中，等待开始'
    case 'running':
      return time ? `${time} · 分析中` : '正在提取考点与错误原因'
    case 'done':
      if (time && duration) return `${time} · 用时 ${duration}`
      if (time) return time
      return props.analysisReady ? '分析结果已就绪' : '分析完成，正在同步结果'
    case 'failed':
      return task?.error_code ? `失败 · ${task.error_code}` : '分析没有成功完成'
    case 'waiting':
      return '等待任务开始'
    default:
      return '等待任务开始'
  }
})

const quizMeta = computed(() => {
  const task = quizTask.value
  const time = taskClock(task)

  switch (quizState.value) {
    case 'queued':
      return task ? '排队中，等待开始' : '生成任务已提交，等待状态同步'
    case 'running':
      return time ? `${time} · 正在生成 3 道题` : '正在生成并校验 3 道题'
    case 'done':
      if (props.generatedCount > 0) {
        return time ? `${time} · ${props.generatedCount} 道` : `${props.generatedCount} 道相似题`
      }
      return '生成完成，正在同步结果'
    case 'failed':
      return task?.error_code ? `失败 · ${task.error_code}` : '生成没有成功完成'
    case 'waiting':
      return props.analysisReady ? '等待生成' : '待分析完成'
    default:
      return '等待生成'
  }
})

const validationMeta = computed(() => {
  switch (validationState.value) {
    case 'queued':
      return '等待生成完成后校验'
    case 'running':
      return '正在校验生成结果'
    case 'done':
      return props.generatedCount > 0 ? `${props.generatedCount} / 3 通过结构校验` : '等待结果同步'
    case 'failed':
      return '校验未通过'
    case 'waiting':
      if (hasFailure.value) return '等待失败任务重试'
      return props.analysisReady ? '等待生成任务开始' : '等待分析完成'
    default:
      return '等待生成结果'
  }
})

const steps = computed<StepView[]>(() => [
  {
    key: 'analysis',
    title: 'AI 分析',
    state: analysisState.value,
    meta: analysisMeta.value,
  },
  {
    key: 'quiz',
    title: '生成相似题',
    state: quizState.value,
    meta: quizMeta.value,
  },
  {
    key: 'validation',
    title: '校验 / 完成',
    state: validationState.value,
    meta: validationMeta.value,
  },
])

const overallTag = computed<{ label: string; className: string; tone: 'done' | 'run' | 'fail' }>(
  () => {
    if (props.timedOut || props.stopped) {
      return { label: '已暂停', className: 'tag--draft', tone: 'run' }
    }
    if (hasActiveProgress.value || props.polling) {
      return { label: '进行中', className: 'tag--run', tone: 'run' }
    }
    if (hasFailure.value) {
      return { label: '需要处理', className: 'tag--fail', tone: 'fail' }
    }
    if (syncPending.value) {
      return { label: '进行中', className: 'tag--run', tone: 'run' }
    }
    if (quizState.value === 'done' && props.generatedCount > 0) {
      return { label: '已完成', className: 'tag--ok', tone: 'done' }
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
  if (props.polling || hasActiveProgress.value || props.generationRequested) {
    return '任务进行中时本页每 1.5 秒自动刷新；失败会显示错误码与重试。'
  }
  if (hasFailure.value || hasFinishedTask.value) {
    return '当前任务已结束，刷新已停止。失败会显示错误码与重试。'
  }
  return '生成相似题后，任务状态会在这里更新；失败会显示错误码与重试。'
})

function stepIcon(state: StepState): Component {
  switch (state) {
    case 'done':
      return IconCheck
    case 'failed':
      return IconClose
    case 'queued':
      return IconClockCircle
    case 'running':
      return IconLoading
    case 'waiting':
      return IconMinus
  }
}

function handleRetry(taskId: number): void {
  emit('retry', taskId)
}
</script>

<template>
  <section class="progress-card" aria-labelledby="progress-title">
    <div class="progress-card__head">
      <h2 id="progress-title">处理进度</h2>
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

    <ol class="flow">
      <li
        v-for="step in steps"
        :key="step.key"
        class="flow__item"
        :class="`flow__item--${step.state}`"
      >
        <span class="flow__mark" :class="`flow__mark--${step.state}`" aria-hidden="true">
          <component
            :is="stepIcon(step.state)"
            class="icon"
            :class="{ 'flow__icon--spin': step.state === 'running' }"
          />
        </span>
        <div class="flow__body">
          <span class="flow__title">{{ step.title }}</span>
          <span class="flow__meta">{{ step.meta }}</span>
        </div>
      </li>
    </ol>

    <div v-for="task in blockingFailedTasks" :key="task.id" class="progress-error" role="alert">
      <p class="progress-error__title">
        {{ taskStageLabel(task.stage) }}任务 #{{ task.id }} 失败
        <span v-if="task.error_code" class="progress-error__code">{{ task.error_code }}</span>
      </p>
      <p class="progress-error__text">{{ taskErrorMessage(task.error_code) }}</p>
      <button
        class="btn btn--quiet btn--sm"
        type="button"
        :disabled="retryingTaskId !== null"
        @click="handleRetry(task.id)"
      >
        {{ retryingTaskId === task.id ? '重试中…' : '重试' }}
      </button>
    </div>

    <div v-if="errorMessage" class="progress-error" role="alert">
      <p class="progress-error__title">
        进度刷新失败
        <span v-if="errorCode" class="progress-error__code">{{ errorCode }}</span>
      </p>
      <p class="progress-error__text">{{ errorMessage }}</p>
      <button class="btn btn--quiet btn--sm" type="button" @click="emit('refresh')">
        重试刷新
      </button>
    </div>

    <p class="progress-note">{{ progressNote }}</p>

    <p class="progress-count">
      已生成 <strong>{{ generatedCount }}</strong> / 3 道相似题
    </p>

    <div class="progress-cta">
      <button
        v-if="generatedCount > 0"
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
        {{ quizState === 'running' ? '生成中…' : '等待生成…' }}
      </button>
      <button
        v-else-if="primaryFailure"
        class="btn btn--danger btn--block"
        type="button"
        :disabled="retryingTaskId !== null"
        @click="handleRetry(primaryFailure.id)"
      >
        {{ retryingTaskId === primaryFailure.id ? '重试中…' : '重试' }}
      </button>
      <button
        v-else
        class="btn btn--primary btn--block"
        type="button"
        :disabled="!analysisReady"
        :title="analysisReady ? undefined : 'AI 分析完成后即可生成相似题'"
        @click="emit('generate')"
      >
        生成相似题
      </button>
    </div>

    <div v-if="polling || showRefreshAction" class="progress-subactions">
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
.progress-card {
  padding: 17px var(--space-5) var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.progress-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.progress-card__head h2 {
  font-size: var(--text-base);
  line-height: 24px;
  font-weight: 650;
}

.progress-card__head .tag {
  flex: none;
}

.flow {
  margin-top: var(--space-5);
}

.flow__item {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding-bottom: 18px;
}

.flow__item:last-child {
  padding-bottom: 0;
}

.flow__item:not(:last-child)::before {
  content: '';
  position: absolute;
  top: 24px;
  bottom: 2px;
  left: 10.5px;
  width: 1px;
  background: var(--color-border);
}

.flow__mark {
  position: relative;
  z-index: 1;
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

.flow__mark .icon {
  width: 12px;
  height: 12px;
}

.flow__mark--done {
  border-color: var(--color-success-border);
  background: var(--color-success-soft);
  color: var(--color-success);
}

.flow__mark--queued,
.flow__mark--running {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary-active);
}

.flow__mark--failed {
  border-color: var(--color-danger-border);
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.flow__icon--spin {
  animation: flow-spin 1s linear infinite;
}

.flow__body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.flow__title {
  display: block;
  color: var(--color-text-1);
  font-size: 15px;
  line-height: 22px;
  font-weight: 600;
}

.flow__meta {
  display: block;
  margin-top: 1px;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
  overflow-wrap: anywhere;
}

.progress-error {
  margin-top: var(--space-4);
  padding: 10px var(--space-3);
  border: 1px solid var(--color-danger-border);
  border-radius: var(--radius-md);
  background: var(--color-danger-soft);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.progress-error__title {
  color: var(--color-text-1);
  font-weight: 600;
}

.progress-error__code {
  margin-left: 2px;
  color: var(--color-danger-text);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 400;
}

.progress-error__text {
  margin-top: 2px;
  text-wrap: pretty;
}

.progress-error .btn {
  margin-top: var(--space-1);
  margin-left: calc(var(--space-2) * -1);
}

.progress-note {
  margin-top: var(--space-4);
  padding: 10px var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.progress-count {
  margin-top: var(--space-4);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.progress-count strong {
  color: var(--color-text-1);
  font-weight: 650;
}

.progress-cta {
  margin-top: 10px;
}

.progress-cta .btn {
  min-height: 44px;
}

.progress-subactions {
  display: flex;
  justify-content: center;
  margin-top: var(--space-2);
}

.progress-subactions .btn {
  min-height: 32px;
}

@keyframes flow-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .flow__icon--spin {
    animation: none;
  }
}

@media (max-width: 767px) {
  .progress-card {
    padding: 15px var(--space-4) var(--space-4);
  }
}
</style>
