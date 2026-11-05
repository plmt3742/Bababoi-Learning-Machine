<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconArrowRight, IconRefresh } from '@arco-design/web-vue/es/icon'
import '@arco-design/web-vue/es/message/style/css.js'
import PageHeader from '../components/common/PageHeader.vue'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import LoadingSkeleton from '../components/common/LoadingSkeleton.vue'
import { getDraft } from '../api/drafts'
import { retryTask } from '../api/tasks'
import { normalizeApiError } from '../api/errors'
import type { Draft, Task, TaskStatus } from '../api/types'
import { useTaskPolling } from '../composables/useTaskPolling'
import { formatDateTime } from '../utils/question'
import { taskErrorMessage, taskStageLabel, taskStatusLabel } from '../utils/task'

type StatusFilter = 'all' | TaskStatus

const STATUS_FILTERS: ReadonlyArray<{ value: StatusFilter; label: string }> = [
  { value: 'all', label: '全部' },
  { value: 'queued', label: '排队中' },
  { value: 'running', label: '生成中' },
  { value: 'done', label: '完成' },
  { value: 'failed', label: '失败' },
]

const router = useRouter()

const {
  tasks,
  polling: isPolling,
  loading: tasksLoading,
  timedOut: pollingTimedOut,
  error: pollingError,
  lastUpdatedAt,
  start: startTaskPolling,
  refresh: refreshTasks,
} = useTaskPolling({ intervalMs: 2000, timeoutMs: 120_000 })

const statusFilter = ref<StatusFilter>('all')
const draft = ref<Draft | null>(null)
const draftLoaded = ref(false)
const draftError = ref('')
const retryingTaskId = ref<number | null>(null)
const manualRefreshing = ref(false)

const filteredTasks = computed(() => {
  if (statusFilter.value === 'all') return tasks.value
  return tasks.value.filter((task) => task.status === statusFilter.value)
})

const statusCounts = computed<Record<StatusFilter, number>>(() => ({
  all: tasks.value.length,
  queued: tasks.value.filter((task) => task.status === 'queued').length,
  running: tasks.value.filter((task) => task.status === 'running').length,
  done: tasks.value.filter((task) => task.status === 'done').length,
  failed: tasks.value.filter((task) => task.status === 'failed').length,
}))

function formatTaskTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  const pad = (part: number) => String(part).padStart(2, '0')
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function formatTaskDuration(task: Task): string {
  if (task.status === 'queued') return '等待开始'
  if (!task.started_at) return task.status === 'running' ? '进行中' : ''

  const startedAt = new Date(task.started_at).getTime()
  const endedAt = task.finished_at ? new Date(task.finished_at).getTime() : Date.now()
  if (Number.isNaN(startedAt) || Number.isNaN(endedAt)) return ''

  if (task.status === 'running') return '自动刷新'

  const seconds = Math.max(0, Math.round((endedAt - startedAt) / 1000))
  return `用时 ${seconds} 秒`
}

const initialLoading = computed(() => {
  if (!draftLoaded.value) return true
  if (lastUpdatedAt.value !== null) return false
  return tasksLoading.value && !pollingError.value
})

const liveStatusText = computed(() => {
  if (isPolling.value) return '自动刷新中 · 每 2 秒'
  if (pollingTimedOut.value) return '等待超时，已暂停自动刷新'
  if (pollingError.value) return '自动刷新失败'
  if (tasks.value.length === 0) return '暂无进行中的任务'
  return '所有任务已结束'
})

const liveStatusTone = computed<'live' | 'paused' | 'error' | 'idle'>(() => {
  if (isPolling.value) return 'live'
  if (pollingTimedOut.value) return 'paused'
  if (pollingError.value) return 'error'
  return 'idle'
})

const lastUpdatedText = computed(() => {
  if (!lastUpdatedAt.value) return ''
  const time = new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(lastUpdatedAt.value)
  return `更新于 ${time}`
})

const draftExcerpt = computed(() => {
  const content = draft.value?.content
  if (!content) return '有未完成的录入草稿'

  const rawContent = content.content_md
  if (typeof rawContent === 'string') {
    const compact = rawContent.replace(/\s+/g, ' ').trim()
    if (compact) return compact.length > 60 ? `${compact.slice(0, 60)}…` : compact
  }

  const rawSubject = content.subject
  if (typeof rawSubject === 'string' && rawSubject.trim()) {
    return `${rawSubject.trim()} · 未完成的录入草稿`
  }

  return '有未完成的录入草稿'
})

const draftUpdatedAt = computed(() => (draft.value ? formatDateTime(draft.value.updated_at) : ''))

async function loadDraft(): Promise<void> {
  draftError.value = ''

  try {
    draft.value = await getDraft()
  } catch (cause) {
    draftError.value = normalizeApiError(cause).message
  } finally {
    draftLoaded.value = true
  }
}

async function handleRefresh(): Promise<void> {
  if (manualRefreshing.value) return

  manualRefreshing.value = true
  try {
    await Promise.all([refreshTasks(), loadDraft()])
  } finally {
    manualRefreshing.value = false
  }
}

async function handleRetry(task: Task): Promise<void> {
  if (retryingTaskId.value !== null) return

  retryingTaskId.value = task.id

  try {
    await retryTask(task.id)
    Message.success(`任务 #${task.id} 已重新提交`)
    startTaskPolling()
  } catch (cause) {
    Message.error(normalizeApiError(cause).message)
  } finally {
    retryingTaskId.value = null
  }
}

function handleEmptyAction(): void {
  if (statusFilter.value === 'all') {
    void router.push('/questions/new')
    return
  }

  statusFilter.value = 'all'
}

onMounted(() => {
  startTaskPolling()
  void loadDraft()
})
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="TASK-01"
      title="任务中心"
      description="跟踪 AI 分析与生题进度，失败可重试；有进行中的任务时自动刷新。"
    />

    <LoadingSkeleton v-if="initialLoading" variant="list" :rows="4" label="正在加载任务" />

    <template v-else>
      <div class="task-toolbar">
        <div class="task-filters" role="group" aria-label="按任务状态筛选">
          <a-button
            v-for="option in STATUS_FILTERS"
            :key="option.value"
            size="small"
            :type="statusFilter === option.value ? 'primary' : 'text'"
            :aria-pressed="statusFilter === option.value"
            @click="statusFilter = option.value"
          >
            {{ option.label }}
            <span class="task-filters__count">{{ statusCounts[option.value] }}</span>
          </a-button>
        </div>

        <div class="task-toolbar__side">
          <div class="task-status" aria-live="polite">
            <span class="task-status__dot" :class="`task-status__dot--${liveStatusTone}`" />
            <span class="task-status__text">{{ liveStatusText }}</span>
            <span v-if="lastUpdatedText" class="task-status__updated">
              {{ lastUpdatedText }}
            </span>
          </div>

          <a-button
            class="task-toolbar__refresh"
            size="small"
            :loading="manualRefreshing"
            :disabled="manualRefreshing"
            @click="handleRefresh"
          >
            <template #icon>
              <IconRefresh />
            </template>
            刷新
          </a-button>
        </div>
      </div>

      <RouterLink v-if="draft" class="draft-row" to="/questions/new">
        <div class="draft-row__main">
          <a-tag size="small" color="orange">草稿</a-tag>
          <span class="draft-row__excerpt">{{ draftExcerpt }}</span>
        </div>
        <span class="draft-row__meta">
          <time :datetime="draft.updated_at">{{ draftUpdatedAt }}</time>
          <span class="draft-row__action">
            继续编辑
            <IconArrowRight />
          </span>
        </span>
      </RouterLink>

      <div v-if="draftError" class="draft-error" role="status">
        <span>草稿加载失败：{{ draftError }}</span>
        <a-button size="mini" type="text" @click="loadDraft">重试</a-button>
      </div>

      <a-alert v-if="pollingError && tasks.length > 0" type="error" show-icon>
        <div class="task-alert">
          <span>
            任务刷新失败：{{ pollingError.message }}
            <span class="task-alert__code">（{{ pollingError.code }}）</span>
          </span>
          <a-button size="mini" type="text" @click="handleRefresh">重试</a-button>
        </div>
      </a-alert>

      <ErrorState
        v-if="pollingError && tasks.length === 0"
        title="任务列表加载失败"
        :message="pollingError.message"
        :code="pollingError.code"
        @retry="handleRefresh"
      />

      <EmptyState
        v-else-if="filteredTasks.length === 0"
        :title="statusFilter === 'all' ? '暂无任务' : '当前筛选下暂无任务'"
        :description="
          statusFilter === 'all'
            ? '录入错题后会自动创建 AI 分析任务，生成相似题也会在这里显示进度。'
            : '换一个状态筛选，或查看全部任务。'
        "
        :action-label="statusFilter === 'all' ? '去录入错题' : '查看全部任务'"
        @action="handleEmptyAction"
      />

      <div v-else class="task-ledger" role="table" aria-label="AI 任务列表">
        <div class="task-ledger__head" role="row">
          <span role="columnheader">任务 / 题目</span>
          <span role="columnheader">阶段</span>
          <span role="columnheader">状态</span>
          <span role="columnheader">时间</span>
          <span class="task-ledger__action-head" role="columnheader">操作</span>
        </div>

        <div
          v-for="task in filteredTasks"
          :key="task.id"
          class="task-ledger__row"
          :class="{ 'task-ledger__row--failed': task.status === 'failed' }"
          role="row"
        >
          <div class="task-ledger__main" role="cell">
            <span class="task-ledger__id">#{{ task.id }}</span>
            <RouterLink
              class="task-question-link"
              :to="`/questions/${task.question_id}`"
              :aria-label="`查看题目 #${task.question_id}`"
            >
              题目 #{{ task.question_id }}
              <IconArrowRight aria-hidden="true" />
            </RouterLink>
          </div>

          <span class="task-ledger__stage" role="cell">{{ taskStageLabel(task.stage) }}</span>

          <span class="task-ledger__status" role="cell">
            <span
              class="task-ledger__dot"
              :class="`task-ledger__dot--${task.status}`"
              aria-hidden="true"
            />
            <span
              class="task-ledger__status-text"
              :class="`task-ledger__status-text--${task.status}`"
            >
              {{ taskStatusLabel(task.status) }}
            </span>
          </span>

          <time class="task-ledger__time" :datetime="task.created_at" role="cell">
            <span class="task-ledger__time-primary">{{ formatTaskTime(task.created_at) }}</span>
            <span class="task-ledger__time-sub">{{ formatTaskDuration(task) }}</span>
          </time>

          <span class="task-ledger__action" role="cell">
            <a-button
              v-if="task.status === 'failed'"
              size="small"
              type="outline"
              status="danger"
              :loading="retryingTaskId === task.id"
              :disabled="retryingTaskId !== null && retryingTaskId !== task.id"
              @click="handleRetry(task)"
            >
              重试
            </a-button>
            <span v-else class="task-ledger__muted">—</span>
          </span>

          <div
            v-if="task.status === 'failed'"
            class="task-ledger__error"
            role="cell"
            :aria-colspan="5"
          >
            <span v-if="task.error_code" class="task-error-code">{{ task.error_code }}</span>
            <span class="task-error-message">{{ taskErrorMessage(task.error_code) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.task-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: 0;
}

.task-toolbar__side {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  margin-left: auto;
}

.task-toolbar__refresh {
  flex: none;
}

.task-status {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.task-status__dot {
  width: var(--space-2);
  height: var(--space-2);
  flex: none;
  border-radius: 50%;
  background: var(--color-text-3);
}

.task-status__dot--live {
  background: var(--color-success);
}

.task-status__dot--paused {
  background: var(--color-warning);
}

.task-status__dot--error {
  background: var(--color-danger);
}

.task-status__dot--idle {
  background: var(--color-text-3);
}

.task-status__updated {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
  font-variant-numeric: tabular-nums;
}

.task-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1);
  min-width: 0;
}

.task-filters :deep(.arco-btn) {
  flex: none;
}

.task-filters :deep(.arco-btn-text) {
  color: var(--color-text-2);
}

.task-filters :deep(.arco-btn-text:hover) {
  color: var(--color-text-1);
}

.task-filters__count {
  margin-left: var(--space-1);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: 1;
  font-variant-numeric: tabular-nums;
  opacity: 0.72;
}

.draft-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  color: inherit;
}

.draft-row:hover {
  border-color: var(--color-primary-hover);
}

.draft-row__main {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1 1 240px;
  min-width: 0;
}

.draft-row__excerpt {
  overflow: hidden;
  color: var(--color-text-1);
  font-size: var(--text-sm);
  font-weight: 500;
  line-height: var(--text-sm-leading);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.draft-row__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-3);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
}

.draft-row__meta time {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.draft-row__action {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-primary);
  font-size: var(--text-sm);
  font-weight: 500;
  line-height: var(--text-sm-leading);
}

.draft-error {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-fill);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.task-alert {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.task-alert__code {
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
}

.task-ledger {
  --task-ledger-columns: minmax(0, 1fr) 86px 106px 158px 84px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.task-ledger__head {
  display: grid;
  grid-template-columns: var(--task-ledger-columns);
  gap: var(--space-3);
  align-items: center;
  min-height: 40px;
  padding: var(--space-2) var(--space-5);
  border-bottom: 1px solid var(--color-border);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  background: var(--color-bg);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  letter-spacing: 0.02em;
}

.task-ledger__action-head {
  text-align: right;
}

.task-ledger__row {
  display: grid;
  grid-template-columns: var(--task-ledger-columns);
  gap: var(--space-2) var(--space-3);
  align-items: center;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}

.task-ledger__row:last-child {
  border-bottom: 0;
}

.task-ledger__row:hover {
  background: var(--color-surface-hover);
}

.task-ledger__row--failed,
.task-ledger__row--failed:hover {
  background: var(--color-danger-soft);
}

.task-ledger__main {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.task-ledger__id {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.task-ledger__stage {
  min-width: 0;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.task-ledger__status {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  white-space: nowrap;
}

.task-ledger__dot {
  width: var(--space-2);
  height: var(--space-2);
  flex: none;
  border-radius: 50%;
  background: var(--color-text-3);
}

.task-ledger__dot--running {
  background: var(--color-primary);
}

.task-ledger__dot--done {
  background: var(--color-success);
}

.task-ledger__dot--failed {
  background: var(--color-danger);
}

.task-ledger__status-text {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  font-weight: 500;
  line-height: var(--text-sm-leading);
}

.task-ledger__status-text--running {
  color: var(--color-primary);
}

.task-ledger__status-text--done {
  color: var(--color-success-text);
}

.task-ledger__status-text--failed {
  color: var(--color-danger-text);
}

.task-question-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  max-width: 100%;
  color: var(--color-text-1);
  font-size: var(--text-sm);
  font-weight: 550;
  line-height: var(--text-sm-leading);
  white-space: nowrap;
}

.task-question-link:hover {
  color: var(--color-primary);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.task-question-link svg {
  width: var(--icon-sm);
  height: var(--icon-sm);
  flex: none;
}

.task-ledger__time {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  color: var(--color-text-2);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
  white-space: nowrap;
}

.task-ledger__time-primary {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.task-ledger__time-sub {
  color: var(--color-text-3);
}

.task-ledger__row--failed .task-ledger__time {
  color: var(--color-text-2);
}

.task-ledger__action {
  display: flex;
  justify-content: flex-end;
  text-align: right;
}

.task-ledger__muted {
  color: var(--color-text-3);
}

.task-ledger__error {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  grid-column: 1 / -1;
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
}

.task-error-code {
  flex: none;
  padding: 1px var(--space-2);
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-danger-text);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
}

.task-error-message {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  overflow-wrap: anywhere;
}

@media (max-width: 767px) {
  .task-toolbar {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-2);
    padding: var(--space-2) 0;
  }

  .task-toolbar__side {
    order: -1;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: var(--space-2);
    margin-left: 0;
  }

  .task-status {
    min-width: 0;
  }

  .task-filters {
    flex-wrap: nowrap;
    width: 100%;
    overflow-x: auto;
    padding-bottom: var(--space-1);
    scrollbar-width: thin;
  }

  .task-filters :deep(.arco-btn) {
    flex: 0 0 auto;
    min-height: 38px;
    padding: 0 var(--space-3);
  }

  .task-filters__count {
    display: none;
  }

  .task-ledger {
    overflow: visible;
    border: 0;
    border-radius: 0;
    background: transparent;
  }

  .task-ledger__head {
    display: none;
  }

  .task-ledger__row {
    grid-template-areas:
      'main status'
      'stage time'
      'error error'
      'action action';
    grid-template-columns: minmax(0, 1fr) auto;
    gap: var(--space-2);
    min-height: 0;
    margin-bottom: var(--space-3);
    padding: var(--space-4);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    background: var(--color-surface);
  }

  .task-ledger__row:not(.task-ledger__row--failed) {
    grid-template-areas:
      'main status'
      'stage time';
  }

  .task-ledger__row:not(.task-ledger__row--failed) .task-ledger__action {
    display: none;
  }

  .task-ledger__row:last-child {
    margin-bottom: 0;
    border-bottom: 1px solid var(--color-border);
  }

  .task-ledger__row--failed,
  .task-ledger__row--failed:hover {
    border-color: var(--color-border-strong);
    background: var(--color-danger-soft);
  }

  .task-ledger__main {
    grid-area: main;
  }

  .task-ledger__stage {
    grid-area: stage;
  }

  .task-ledger__status {
    grid-area: status;
    justify-self: end;
  }

  .task-ledger__time {
    grid-area: time;
    align-items: flex-end;
    text-align: right;
  }

  .task-ledger__action {
    grid-area: action;
    justify-self: stretch;
  }

  .task-ledger__action :deep(.arco-btn) {
    width: 100%;
    min-height: 38px;
  }

  .task-ledger__error {
    grid-area: error;
  }

  .draft-row__meta {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
