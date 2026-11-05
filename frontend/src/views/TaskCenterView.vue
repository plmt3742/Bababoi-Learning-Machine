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
import { taskErrorMessage, taskStageLabel, taskStatusColor, taskStatusLabel } from '../utils/task'

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
    >
      <template #actions>
        <a-button :loading="manualRefreshing" :disabled="manualRefreshing" @click="handleRefresh">
          <template #icon>
            <IconRefresh />
          </template>
          刷新
        </a-button>
      </template>
    </PageHeader>

    <LoadingSkeleton v-if="initialLoading" variant="list" :rows="4" label="正在加载任务" />

    <template v-else>
      <div v-if="tasks.length > 0" class="task-toolbar">
        <div class="task-status" aria-live="polite">
          <span class="task-status__dot" :class="`task-status__dot--${liveStatusTone}`" />
          <span class="task-status__text">{{ liveStatusText }}</span>
          <span v-if="lastUpdatedText" class="task-status__updated">
            {{ lastUpdatedText }}
          </span>
        </div>

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

      <ul v-else class="task-list">
        <li v-for="task in filteredTasks" :key="task.id" class="task-row">
          <div class="task-row__main">
            <div class="task-row__topline">
              <span class="task-row__id">#{{ task.id }}</span>
              <a-tag size="small" :color="taskStatusColor(task.status)">
                {{ taskStatusLabel(task.status) }}
              </a-tag>
              <a-tag size="small" color="gray">{{ taskStageLabel(task.stage) }}</a-tag>
            </div>

            <RouterLink class="task-row__question" :to="`/questions/${task.question_id}`">
              题目 #{{ task.question_id }}
              <IconArrowRight />
            </RouterLink>

            <p v-if="task.status === 'failed'" class="task-row__error">
              <span v-if="task.error_code" class="task-row__error-code">
                {{ task.error_code }}
              </span>
              <span>{{ taskErrorMessage(task.error_code) }}</span>
            </p>
          </div>

          <div class="task-row__meta">
            <time class="task-row__time" :datetime="task.created_at">
              {{ formatDateTime(task.created_at) }}
            </time>
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
          </div>
        </li>
      </ul>
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
  border-radius: var(--radius-sm);
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
}

.task-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
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
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.task-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.task-row__main {
  display: flex;
  flex: 1 1 320px;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}

.task-row__topline {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.task-row__id {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
}

.task-row__question {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  width: fit-content;
  max-width: 100%;
  color: var(--color-text-1);
  font-size: var(--text-sm);
  font-weight: 500;
  line-height: var(--text-sm-leading);
  overflow-wrap: anywhere;
}

.task-row__question:hover {
  color: var(--color-primary);
}

.task-row__error {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-2);
  margin: 0;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  overflow-wrap: anywhere;
}

.task-row__error-code {
  flex: none;
  color: var(--color-danger);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
}

.task-row__meta {
  display: flex;
  flex-direction: column;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: var(--space-2);
}

.task-row__time {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
}

@media (max-width: 767px) {
  .task-toolbar {
    align-items: flex-start;
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
  }

  .task-row__meta {
    width: 100%;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }

  .draft-row__meta {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
