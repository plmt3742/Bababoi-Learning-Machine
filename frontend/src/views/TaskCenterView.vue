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

const filterCounts = computed<Record<StatusFilter, number>>(() => {
  const counts: Record<StatusFilter, number> = {
    all: tasks.value.length,
    queued: 0,
    running: 0,
    done: 0,
    failed: 0,
  }

  for (const task of tasks.value) {
    counts[task.status] += 1
  }

  return counts
})

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

const draftUpdatedAt = computed(() =>
  draft.value ? formatTaskTime(draft.value.updated_at, false) : '',
)

function toDate(value: string | null | undefined): Date | null {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function pad2(value: number): string {
  return String(value).padStart(2, '0')
}

/** Compact ledger timestamp: `MM-DD HH:mm` (or with seconds for task rows). */
function formatTaskTime(value: string | null | undefined, withSeconds = true): string {
  const date = toDate(value)
  if (!date) return '—'

  const base = `${pad2(date.getMonth() + 1)}-${pad2(date.getDate())} ${pad2(date.getHours())}:${pad2(
    date.getMinutes(),
  )}`

  return withSeconds ? `${base}:${pad2(date.getSeconds())}` : base
}

/**
 * Terminal tasks measure from start to finish; active tasks never turn the
 * elapsed wall-clock time into a stale, ever-growing duration.
 */
function formatTaskDuration(task: Task): string {
  if (task.status === 'queued') return '等待开始'
  if (task.status === 'running') return '自动刷新'

  const finishedAt = toDate(task.finished_at)
  const startedAt = toDate(task.started_at) ?? toDate(task.created_at)
  if (!finishedAt || !startedAt) return '已结束'

  const seconds = Math.max(0, Math.round((finishedAt.getTime() - startedAt.getTime()) / 1000))
  if (seconds < 60) return `用时 ${seconds} 秒`

  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return rest === 0 ? `用时 ${minutes} 分` : `用时 ${minutes} 分 ${rest} 秒`
}

function taskStatusText(status: TaskStatus): string {
  return status === 'running' ? '生成中' : taskStatusLabel(status)
}

function taskStatusTagClass(status: TaskStatus): string {
  if (status === 'done') return 'tag tag--ok'
  if (status === 'failed') return 'tag tag--fail'
  if (status === 'running') return 'tag tag--run'
  return 'tag'
}

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
      eyebrow="Task ledger"
      title="任务中心"
      description="跟踪 AI 分析与生题进度，失败可重试；有进行中的任务时自动刷新。"
    >
      <template #actions>
        <button
          class="btn btn--outline task-refresh"
          type="button"
          :disabled="manualRefreshing"
          :aria-busy="manualRefreshing"
          @click="handleRefresh"
        >
          <IconRefresh />
          刷新
        </button>
      </template>
    </PageHeader>

    <LoadingSkeleton v-if="initialLoading" variant="list" :rows="4" label="正在加载任务" />

    <template v-else>
      <div class="task-toolbar">
        <p class="task-status" role="status">
          <span
            class="task-status__dot"
            :class="`task-status__dot--${liveStatusTone}`"
            aria-hidden="true"
          />
          {{ liveStatusText }}
          <span v-if="lastUpdatedText" class="task-status__updated">{{ lastUpdatedText }}</span>
        </p>

        <div class="task-filters" role="group" aria-label="按任务状态筛选">
          <button
            v-for="option in STATUS_FILTERS"
            :key="option.value"
            type="button"
            class="filter-btn"
            :aria-pressed="statusFilter === option.value"
            @click="statusFilter = option.value"
          >
            {{ option.label }}
            <span class="filter-btn__count">{{ filterCounts[option.value] }}</span>
          </button>
        </div>
      </div>

      <RouterLink v-if="draft" class="draft-bar" to="/questions/new">
        <span class="tag tag--draft">草稿</span>
        <span class="draft-bar__text">
          {{ draftExcerpt }}
          <span class="draft-bar__sub">未完成的录入，已自动保存</span>
        </span>
        <span class="draft-bar__meta">
          <time class="draft-bar__time" :datetime="draft.updated_at">{{ draftUpdatedAt }}</time>
          <span class="draft-bar__go">
            继续编辑
            <IconArrowRight aria-hidden="true" />
          </span>
        </span>
      </RouterLink>

      <div v-if="draftError" class="draft-error" role="status">
        <span>草稿加载失败：{{ draftError }}</span>
        <button class="btn btn--quiet btn--sm" type="button" @click="loadDraft">重试</button>
      </div>

      <a-alert
        v-if="pollingError && tasks.length > 0"
        class="task-alert-box"
        type="error"
        show-icon
      >
        <div class="task-alert">
          <span>
            任务刷新失败：{{ pollingError.message }}
            <span class="task-alert__code">（{{ pollingError.code }}）</span>
          </span>
          <button class="btn btn--quiet btn--sm" type="button" @click="handleRefresh">重试</button>
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

      <section v-else class="task-panel" aria-label="任务列表">
        <div class="task-head">
          <span>任务 / 题目</span>
          <span>阶段</span>
          <span>状态</span>
          <span>时间</span>
          <span>操作</span>
        </div>

        <ul class="task-list">
          <li
            v-for="task in filteredTasks"
            :key="task.id"
            class="task-row"
            :class="{ 'task-row--failed': task.status === 'failed' }"
          >
            <div class="task-row__main">
              <span class="task-row__id">#{{ task.id }}</span>
              <RouterLink class="task-row__link" :to="`/questions/${task.question_id}`">
                题目 #{{ task.question_id }}
                <IconArrowRight aria-hidden="true" />
              </RouterLink>
            </div>

            <div class="task-row__stage">{{ taskStageLabel(task.stage) }}</div>

            <div class="task-row__status">
              <span :class="taskStatusTagClass(task.status)">
                <span v-if="task.status === 'running'" class="dot" aria-hidden="true" />
                {{ taskStatusText(task.status) }}
              </span>
            </div>

            <div class="task-row__time">
              <time :datetime="task.created_at">{{ formatTaskTime(task.created_at) }}</time>
              <span class="task-row__time-sub">{{ formatTaskDuration(task) }}</span>
            </div>

            <div class="task-row__action">
              <button
                v-if="task.status === 'failed'"
                class="btn btn--danger btn--sm"
                type="button"
                :disabled="retryingTaskId !== null"
                :aria-busy="retryingTaskId === task.id"
                @click="handleRetry(task)"
              >
                {{ retryingTaskId === task.id ? '重试中…' : '重试' }}
              </button>
              <span v-else class="muted">—</span>
            </div>

            <p v-if="task.status === 'failed'" class="task-row__error">
              <code v-if="task.error_code" class="task-row__error-code">
                {{ task.error_code }}
              </code>
              <span>{{ taskErrorMessage(task.error_code) }}</span>
              <span v-if="task.retry_index > 0" class="task-row__error-meta">
                第 {{ task.retry_index + 1 }} 次尝试
              </span>
            </p>
          </li>
        </ul>
      </section>

      <p v-if="filteredTasks.length > 0" class="task-foot">
        共 {{ filteredTasks.length }} 条任务 · 任务结束后自动停止刷新 · 失败任务保留错误码
      </p>
    </template>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
}

.task-refresh:disabled :deep(svg) {
  animation: task-refresh-spin 0.9s linear infinite;
}

@keyframes task-refresh-spin {
  to {
    transform: rotate(360deg);
  }
}

.task-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
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
  width: 6px;
  height: 6px;
  flex: none;
  border-radius: 50%;
  background: var(--color-text-3);
}

.task-status__dot--live {
  background: var(--color-success);
  box-shadow: 0 0 0 3px var(--color-success-soft);
  animation: calm-soft-pulse 1.8s ease-in-out infinite;
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
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.task-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1);
}

.filter-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  min-height: 34px;
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: 1;
}

.filter-btn:hover {
  background: var(--color-fill);
  color: var(--color-text-1);
}

.filter-btn[aria-pressed='true'] {
  background: var(--color-primary-soft);
  color: var(--color-primary-active);
  font-weight: 650;
}

.filter-btn__count {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 400;
}

.filter-btn[aria-pressed='true'] .filter-btn__count {
  color: var(--color-primary-active);
}

.draft-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 9px;
  margin-bottom: var(--space-4);
  padding: 11px var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  color: inherit;
  transition: border-color 0.15s ease;
}

.draft-bar:hover {
  border-color: var(--color-border-strong);
  color: inherit;
}

.draft-bar__text {
  flex: 1 1 auto;
  min-width: 0;
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 500;
  overflow-wrap: anywhere;
}

.draft-bar__sub {
  color: var(--color-text-3);
  font-weight: 400;
}

.draft-bar__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  margin-left: auto;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.draft-bar__time {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

.draft-bar__go {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--color-primary-active);
  font-weight: 500;
}

.draft-bar:hover .draft-bar__go {
  color: var(--color-primary);
}

.draft-bar__go :deep(svg) {
  width: 15px;
  height: 15px;
}

.draft-error {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-fill);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.task-alert-box {
  margin-bottom: var(--space-4);
}

.task-alert {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.task-alert__code {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.task-panel {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.task-head,
.task-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 86px 106px 158px 84px;
  align-items: center;
  gap: 14px;
}

.task-head {
  padding: 9px var(--space-5);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface-subtle);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  letter-spacing: 0.02em;
}

.task-list {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
}

.task-row {
  padding: 14px var(--space-5);
  border-bottom: 1px solid var(--color-border);
  row-gap: var(--space-2);
}

.task-row:last-child {
  border-bottom: 0;
}

.task-row:hover {
  background: var(--color-surface-hover);
}

.task-row--failed {
  background: var(--color-danger-soft);
}

.task-row--failed:hover {
  background: var(--color-danger-soft);
}

.task-row__main {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.task-row__id {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  letter-spacing: 0.02em;
}

.task-row__link {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  min-width: 0;
  color: var(--color-text-1);
  font-size: 15px;
  line-height: var(--text-sm-leading);
  font-weight: 600;
  overflow-wrap: anywhere;
}

.task-row__link:hover {
  color: var(--color-primary-active);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.task-row__link :deep(svg) {
  width: 14px;
  height: 14px;
  flex: none;
  color: var(--color-text-3);
}

.task-row__stage {
  min-width: 0;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.task-row__status {
  justify-self: start;
}

.task-row__time {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.task-row__time time {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

.task-row__time-sub {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: 20px;
}

.task-row__action {
  justify-self: start;
}

.task-row__error {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 9px;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  overflow-wrap: anywhere;
}

.task-row__error-code {
  color: var(--color-danger);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 600;
}

.task-row__error-meta {
  color: var(--color-text-3);
}

.task-foot {
  margin-top: var(--space-3);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

@media (max-width: 767px) {
  .task-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-2);
  }

  .task-filters {
    flex-wrap: nowrap;
    width: 100%;
    overflow-x: auto;
    padding-bottom: var(--space-1);
    scrollbar-width: thin;
  }

  .filter-btn {
    flex: 0 0 auto;
  }

  .filter-btn__count {
    display: none;
  }

  .draft-bar {
    align-items: flex-start;
  }

  .draft-bar__meta {
    width: 100%;
    margin-left: 0;
    justify-content: space-between;
  }

  .task-head {
    display: none;
  }

  .task-row {
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-areas:
      'main status'
      'stage time';
    gap: var(--space-2) var(--space-3);
    padding: 14px var(--space-4);
  }

  .task-row--failed {
    grid-template-areas:
      'main status'
      'stage time'
      'error error'
      'action action';
  }

  .task-row__main {
    grid-area: main;
    align-self: center;
  }

  .task-row__stage {
    grid-area: stage;
    align-self: center;
  }

  .task-row__status {
    grid-area: status;
    justify-self: end;
    align-self: center;
  }

  .task-row__time {
    grid-area: time;
    align-items: flex-end;
    text-align: right;
  }

  .task-row__error {
    grid-area: error;
  }

  .task-row__action {
    grid-area: action;
    width: 100%;
  }

  .task-row:not(.task-row--failed) .task-row__action {
    display: none;
  }

  .task-row__action .btn {
    width: 100%;
    min-height: 38px;
  }

  .task-foot {
    margin-top: var(--space-2);
  }
}
</style>
