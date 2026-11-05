<script setup lang="ts">
import { computed } from 'vue'
import { IconArrowRight, IconRecordStop, IconRefresh } from '@arco-design/web-vue/es/icon'
import type { Task } from '../../api/types'
import { hasActiveTasks, latestTask, taskErrorMessage, taskStageLabel } from '../../utils/task'

type StepState = 'waiting' | 'queued' | 'running' | 'done' | 'failed'

interface StepView {
  key: 'analysis' | 'quiz' | 'validation'
  no: string
  title: string
  state: StepState
  status: string
  description: string
  taskId: number | null
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
const hasActiveProgress = computed(
  () =>
    analysisState.value === 'queued' ||
    analysisState.value === 'running' ||
    quizState.value === 'queued' ||
    quizState.value === 'running',
)
const hasRunningStep = computed(
  () => analysisState.value === 'running' || quizState.value === 'running',
)
const syncPending = computed(
  () =>
    (analysisState.value === 'done' && !props.analysisReady) ||
    (quizState.value === 'done' && props.generatedCount === 0),
)

function stepStatusLabel(state: StepState, kind: StepView['key']): string {
  switch (state) {
    case 'queued':
      return '排队中'
    case 'running':
      if (kind === 'analysis') return '分析中'
      if (kind === 'quiz') return '生成中'
      return '处理中'
    case 'done':
      return '已完成'
    case 'failed':
      return '失败'
    case 'waiting':
      return '待开始'
    default:
      return '待开始'
  }
}

const analysisDescription = computed(() => {
  switch (analysisState.value) {
    case 'queued':
      return '分析任务已入队，等待开始。'
    case 'running':
      return '正在提取知识点、错误原因与解题摘要。'
    case 'done':
      return props.analysisReady ? '分析结果已就绪。' : '分析完成，正在同步结果。'
    case 'failed':
      return '分析没有成功完成，可以重试。'
    case 'waiting':
      return '录入后将自动开始分析。'
    default:
      return '等待任务开始。'
  }
})

const quizDescription = computed(() => {
  switch (quizState.value) {
    case 'queued':
      return quizTask.value ? '生成任务已入队，等待开始。' : '生成任务已提交，等待状态同步。'
    case 'running':
      return '正在生成并校验 3 道相似题。'
    case 'done':
      return props.generatedCount > 0
        ? `已生成 ${props.generatedCount}/3 道相似题。`
        : '生成完成，正在同步题目。'
    case 'failed':
      return '相似题生成没有成功完成，可以重试。'
    case 'waiting':
      return props.analysisReady ? '可以点击「生成相似题」开始。' : '分析完成后可生成相似题。'
    default:
      return '等待生成任务。'
  }
})

const validationDescription = computed(() => {
  switch (validationState.value) {
    case 'queued':
      return '等待生成完成后校验结果。'
    case 'running':
      return '正在校验生成结果。'
    case 'done':
      return props.generatedCount > 0
        ? '已完成校验，结果已同步到本页。'
        : '生成完成，等待结果同步。'
    case 'waiting':
      return '等待生成任务开始。'
    default:
      return '等待生成结果。'
  }
})

const steps = computed<StepView[]>(() => [
  {
    key: 'analysis',
    no: '01',
    title: 'AI 分析',
    state: analysisState.value,
    status: stepStatusLabel(analysisState.value, 'analysis'),
    description: analysisDescription.value,
    taskId: analysisTask.value?.id ?? null,
  },
  {
    key: 'quiz',
    no: '02',
    title: '生成相似题',
    state: quizState.value,
    status: stepStatusLabel(quizState.value, 'quiz'),
    description: quizDescription.value,
    taskId: quizTask.value?.id ?? null,
  },
  {
    key: 'validation',
    no: '03',
    title: '校验 / 完成',
    state: validationState.value,
    status: stepStatusLabel(validationState.value, 'validation'),
    description: validationDescription.value,
    taskId: null,
  },
])

const headline = computed(() => {
  if (quizState.value === 'running') return '正在生成相似题'
  if (quizState.value === 'queued') return '相似题任务已入队'
  if (analysisState.value === 'running') return '正在分析这道题'
  if (analysisState.value === 'queued') return '分析任务已入队'
  if (syncPending.value) return '任务完成，正在同步结果'
  if (hasFailure.value) return '任务遇到问题，可重试'
  if (quizState.value === 'done' && props.generatedCount > 0) return '相似题已生成完成'
  if (quizState.value === 'done') return '生成完成，正在同步结果'
  if (props.polling) return '正在等待任务更新'
  if (props.timedOut || props.stopped) return '已暂停等待'
  return '任务处理中'
})

const progressPercent = computed(() => {
  if (quizState.value === 'failed') return 66
  if (quizState.value === 'done') return props.generatedCount > 0 ? 100 : 94
  if (quizState.value === 'running') return 74
  if (quizState.value === 'queued') return 48
  if (analysisState.value === 'failed') return 18
  if (analysisState.value === 'done') return 34
  if (analysisState.value === 'running') return 20
  if (analysisState.value === 'queued') return 8
  return 4
})

const progressTone = computed<'normal' | 'success' | 'danger'>(() => {
  if (progressPercent.value === 100) return 'success'
  if (hasFailure.value && !hasActiveProgress.value) return 'danger'
  return 'normal'
})

const progressBarStyle = computed(() => ({
  transform: `scaleX(${progressPercent.value / 100})`,
}))

const overallTag = computed<{ color: string; label: string }>(() => {
  if (progressPercent.value === 100) return { color: 'green', label: '已完成' }
  if (hasActiveProgress.value) {
    return { color: 'arcoblue', label: hasRunningStep.value ? '进行中' : '排队中' }
  }
  if (syncPending.value) return { color: 'arcoblue', label: '同步中' }
  if (hasFailure.value) return { color: 'red', label: '需要处理' }
  if (props.polling) return { color: 'arcoblue', label: '进行中' }
  if (props.timedOut || props.stopped) return { color: 'orange', label: '已暂停' }
  return { color: 'gray', label: '等待中' }
})

function handleRetry(taskId: number): void {
  emit('retry', taskId)
}
</script>

<template>
  <a-card class="generation-progress" :bordered="false">
    <header class="generation-progress__header">
      <div class="generation-progress__heading">
        <p class="generation-progress__eyebrow">AI GENERATION</p>
        <h2 class="generation-progress__title">AI 生成进度</h2>
        <p class="generation-progress__headline">{{ headline }}</p>
      </div>
      <a-tag :color="overallTag.color">{{ overallTag.label }}</a-tag>
    </header>

    <div
      class="generation-progress__track"
      role="progressbar"
      aria-label="AI 生成进度"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-valuenow="progressPercent"
    >
      <div
        class="generation-progress__bar"
        :class="`generation-progress__bar--${progressTone}`"
        :style="progressBarStyle"
      />
    </div>

    <ol class="generation-progress__steps">
      <li
        v-for="step in steps"
        :key="step.key"
        class="generation-progress__step"
        :class="`generation-progress__step--${step.state}`"
      >
        <span class="generation-progress__step-index" aria-hidden="true">{{ step.no }}</span>
        <div class="generation-progress__step-body">
          <div class="generation-progress__step-heading">
            <h3 class="generation-progress__step-title">{{ step.title }}</h3>
            <span class="generation-progress__step-status">
              {{ step.status }}
              <span v-if="step.taskId" class="generation-progress__step-task">
                #{{ step.taskId }}
              </span>
            </span>
          </div>
          <p class="generation-progress__step-description">{{ step.description }}</p>
        </div>
      </li>
    </ol>

    <a-alert v-if="errorMessage" type="error" :show-icon="true" class="generation-progress__alert">
      <div class="generation-progress__alert-body">
        <span>
          进度刷新失败：{{ errorMessage }}
          <span v-if="errorCode" class="generation-progress__error-code">（{{ errorCode }}）</span>
        </span>
        <a-button size="mini" type="text" @click="emit('refresh')">重试</a-button>
      </div>
    </a-alert>

    <a-alert v-if="timedOut" type="warning" :show-icon="true" class="generation-progress__alert">
      等待超过 2 分钟，已暂停自动刷新。服务器任务可能仍在继续，可点击「刷新一次」查看最新状态。
    </a-alert>
    <a-alert v-else-if="stopped" type="info" :show-icon="true" class="generation-progress__alert">
      已暂停自动刷新。服务器任务仍在继续，可点击「刷新一次」查看最新状态，或前往任务中心。
    </a-alert>

    <div v-for="task in blockingFailedTasks" :key="task.id" class="generation-progress__failure">
      <a-alert type="error" :show-icon="true">
        <div class="generation-progress__failure-body">
          <div class="generation-progress__failure-copy">
            <p class="generation-progress__failure-title">
              {{ taskStageLabel(task.stage) }}任务
              <span class="generation-progress__task-id">#{{ task.id }}</span>
              失败
              <span v-if="task.error_code" class="generation-progress__error-code">
                {{ task.error_code }}
              </span>
            </p>
            <p class="generation-progress__failure-message">
              {{ taskErrorMessage(task.error_code) }}
            </p>
          </div>
          <a-button
            size="small"
            status="danger"
            type="outline"
            :loading="retryingTaskId === task.id"
            :disabled="retryingTaskId !== null && retryingTaskId !== task.id"
            @click="handleRetry(task.id)"
          >
            重试任务
          </a-button>
        </div>
      </a-alert>
    </div>

    <footer class="generation-progress__footer">
      <div class="generation-progress__actions">
        <a-button v-if="polling" size="small" type="outline" @click="emit('stop')">
          <template #icon>
            <IconRecordStop />
          </template>
          暂停自动刷新
        </a-button>
        <a-button
          v-else
          size="small"
          :loading="loading"
          :disabled="loading"
          @click="emit('refresh')"
        >
          <template #icon>
            <IconRefresh />
          </template>
          刷新一次
        </a-button>

        <RouterLink class="generation-progress__tasks-link" to="/tasks">
          任务中心
          <IconArrowRight />
        </RouterLink>
      </div>

      <p class="generation-progress__hint">
        {{
          polling
            ? '「暂停自动刷新」只会暂停本页刷新，服务器任务仍会继续。'
            : hasActiveTask
              ? '本页已暂停自动刷新，服务器任务仍会继续。'
              : '任务已结束，可前往任务中心查看全部记录。'
        }}
      </p>
    </footer>
  </a-card>
</template>

<style scoped>
.generation-progress {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.generation-progress :deep(.arco-card-body) {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-5);
}

.generation-progress__header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.generation-progress__heading {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.generation-progress__eyebrow {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
  letter-spacing: 0.08em;
}

.generation-progress__title {
  font-size: var(--text-lg);
  line-height: var(--text-lg-leading);
}

.generation-progress__headline {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.generation-progress__track {
  height: 6px;
  overflow: hidden;
  border-radius: var(--radius-sm);
  background: var(--color-fill);
}

.generation-progress__bar {
  width: 100%;
  height: 100%;
  border-radius: inherit;
  background: var(--color-primary);
  transform-origin: left center;
  transition: transform 240ms ease;
}

.generation-progress__bar--success {
  background: var(--color-success);
}

.generation-progress__bar--danger {
  background: var(--color-danger);
}

.generation-progress__steps {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.generation-progress__step {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.generation-progress__step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: 30px;
  height: 24px;
  margin-top: 1px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: 1;
  letter-spacing: 0.04em;
}

.generation-progress__step--queued .generation-progress__step-index,
.generation-progress__step--running .generation-progress__step-index {
  border-color: var(--color-primary);
  background: var(--color-primary-softer);
  color: var(--color-primary);
}

.generation-progress__step--done .generation-progress__step-index {
  border-color: var(--color-success);
  background: var(--color-success-soft);
  color: var(--color-success-text);
}

.generation-progress__step--failed .generation-progress__step-index {
  border-color: var(--color-danger);
  background: var(--color-danger-soft);
  color: var(--color-danger-text);
}

.generation-progress__step-body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.generation-progress__step-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
}

.generation-progress__step-title {
  font-size: var(--text-sm);
  font-weight: 600;
  line-height: var(--text-sm-leading);
}

.generation-progress__step-status {
  display: inline-flex;
  align-items: baseline;
  gap: var(--space-2);
  flex: none;
  color: var(--color-text-3);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
}

.generation-progress__step-task {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.generation-progress__step--queued .generation-progress__step-status,
.generation-progress__step--running .generation-progress__step-status {
  color: var(--color-primary);
}

.generation-progress__step--done .generation-progress__step-status {
  color: var(--color-success-text);
}

.generation-progress__step--failed .generation-progress__step-status {
  color: var(--color-danger-text);
}

.generation-progress__step-description {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.generation-progress__alert {
  align-items: flex-start;
}

.generation-progress__alert-body {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.generation-progress__error-code {
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
}

.generation-progress__failure-body {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.generation-progress__failure-copy {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.generation-progress__failure-title {
  color: var(--color-text-1);
  font-size: var(--text-sm);
  font-weight: 600;
  line-height: var(--text-sm-leading);
  overflow-wrap: anywhere;
}

.generation-progress__task-id {
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.generation-progress__failure-message {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.generation-progress__footer {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
}

.generation-progress__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.generation-progress__tasks-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.generation-progress__tasks-link:hover {
  color: var(--color-primary);
}

.generation-progress__hint {
  color: var(--color-text-3);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
  text-wrap: pretty;
}

@media (prefers-reduced-motion: reduce) {
  .generation-progress__bar {
    transition: none;
  }
}

@media (max-width: 767px) {
  .generation-progress :deep(.arco-card-body) {
    padding: var(--space-4);
  }
}
</style>
