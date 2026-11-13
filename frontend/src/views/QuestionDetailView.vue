<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconArrowLeft, IconDelete, IconEdit, IconRefresh } from '@arco-design/web-vue/es/icon'
import '@arco-design/web-vue/es/message/style/css.js'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import LoadingSkeleton from '../components/common/LoadingSkeleton.vue'
import MarkdownRenderer from '../components/common/MarkdownRenderer.vue'
import GenerationProgress from '../components/ai/GenerationProgress.vue'
import GenerationSegments from '../components/ai/GenerationSegments.vue'
import AnalysisCard from '../components/question/AnalysisCard.vue'
import GeneratedQuestionCard from '../components/question/GeneratedQuestionCard.vue'
import { generateQuestions, getQuestion, removeQuestion } from '../api/questions'
import { retryTask } from '../api/tasks'
import { normalizeApiError } from '../api/errors'
import type { QuestionDetail, Task } from '../api/types'
import { useTaskPolling } from '../composables/useTaskPolling'
import { hasActiveTasks, latestTask } from '../utils/task'
import { isSegmentTask, summarizeSegments } from '../utils/segments'
import { formatDateTime, masteryStatusLabel, questionTypeLabel } from '../utils/question'
import { parseApiTime } from '../utils/time'

const route = useRoute()
const router = useRouter()

const question = ref<QuestionDetail | null>(null)
const loading = ref(true)
const errorMessage = ref('')
const errorCode = ref('')
const notFound = ref(false)

const deleteDialogVisible = ref(false)
const deleteError = ref('')
const deleting = ref(false)
const submittingGeneration = ref(false)
const refreshing = ref(false)
const generationRequested = ref(false)
const generationMode = ref<'legacy' | 'segments'>('legacy')
const actionError = ref('')
const retryingTaskId = ref<number | null>(null)
const refreshQueued = ref(false)

const handledDoneTaskIds = new Set<number>()
let knownQuizTaskId = 0
let loadToken = 0

const questionId = computed<number | null>(() => {
  const raw = route.params.id
  const value = Array.isArray(raw) ? raw[0] : raw
  if (!value) return null

  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) && parsed > 0 && String(parsed) === value ? parsed : null
})

const {
  tasks: liveTasks,
  polling: isPolling,
  loading: tasksLoading,
  timedOut: pollingTimedOut,
  stopped: pollingStopped,
  error: pollingError,
  start: startTaskPolling,
  stop: stopTaskPolling,
  refresh: refreshTasks,
  reset: resetTaskPolling,
  setTasks: setPollingTasks,
} = useTaskPolling({
  questionId: () => questionId.value,
  intervalMs: 1500,
  timeoutMs: 120_000,
})

const createdAt = computed(() => (question.value ? formatDateTime(question.value.created_at) : ''))
const detailSubtitle = computed(() => {
  const current = question.value
  if (!current) return ''

  const parts = [current.subject]
  if (current.chapter) parts.push(current.chapter)
  if (createdAt.value) parts.push(`录入于 ${createdAt.value}`)
  return parts.join(' · ')
})
const masteryTagClass = computed(() => {
  const status = question.value?.mastery_status
  if (status === 'mastered') return 'tag--mastered'
  if (status === 'unmastered') return 'tag--unmastered'
  return 'tag--reviewing'
})

const hasAnswer = computed(() => Boolean(question.value?.answer_md?.trim()))
const hasExplanation = computed(() => Boolean(question.value?.explanation_md?.trim()))
const blanks = computed(() => question.value?.blanks ?? [])
const hasAnswerContent = computed(() => hasAnswer.value || blanks.value.length > 0)
const hasAnyQa = computed(() => hasAnswerContent.value || hasExplanation.value)
const sortedGeneratedQuestions = computed(() => {
  const items = question.value?.generated_questions ?? []
  const hasTargetIndex = items.some(
    (item) => item.target_index !== null && item.target_index !== undefined,
  )
  if (!hasTargetIndex) return items

  return [...items].sort((left, right) => (left.target_index ?? 99) - (right.target_index ?? 99))
})
const generatedCount = computed(() => sortedGeneratedQuestions.value.length)
const allGeneratedValid = computed(() => {
  const items = question.value?.generated_questions ?? []
  return items.length > 0 && items.every((item) => item.validation_status === 'valid')
})
const analysisReady = computed(() => Boolean(question.value?.analysis))

const analysisTask = computed(() => latestTask(liveTasks.value, 'analysis'))
const legacyTasks = computed(() => liveTasks.value.filter((task) => !isSegmentTask(task)))
const legacyQuizTask = computed(() => latestTask(legacyTasks.value, 'quiz'))
const segmentSummary = computed(() => summarizeSegments(liveTasks.value))
const segmentActive = computed(() => segmentSummary.value.activeCount > 0)

const analysisPending = computed(
  () =>
    !analysisReady.value &&
    (analysisTask.value?.status === 'queued' || analysisTask.value?.status === 'running'),
)
const analysisFailed = computed(
  () => !analysisReady.value && analysisTask.value?.status === 'failed',
)
const quizActive = computed(() => {
  if (generationMode.value === 'segments') return segmentActive.value
  return legacyQuizTask.value?.status === 'queued' || legacyQuizTask.value?.status === 'running'
})
const generationBusy = computed(() => quizActive.value || generationRequested.value)

const analysisTaskLabel = computed(() => {
  const task = analysisTask.value
  if (!task) return ''

  const date = parseApiTime(task.started_at ?? task.created_at)
  if (Number.isNaN(date.getTime())) return `任务 #${task.id}`

  const time = new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date)
  return `任务 #${task.id} · ${time}`
})

const generatedEmptyHint = computed(() => {
  if (generationBusy.value) return '相似题正在生成，完成后会自动出现在这里。'
  if (generationMode.value === 'segments' && segmentSummary.value.failedCount > 0) {
    return '部分相似题生成失败，可在右侧处理进度中单独重试失败段。'
  }
  if (analysisPending.value) return 'AI 分析完成后，即可在右侧生成 3 道相似题。'
  if (analysisFailed.value) return '分析任务未成功完成，处理后可生成相似题。'
  if (!analysisReady.value) return 'AI 分析完成后，即可在右侧生成 3 道相似题。'
  return '点击右侧「生成相似题」，完成后会在本页展示 3 道题。'
})

function rememberLatestQuizTask(tasks: Task[]): void {
  const latestQuizTask = latestTask(tasks, 'quiz')
  if (latestQuizTask && latestQuizTask.id > knownQuizTaskId) {
    knownQuizTaskId = latestQuizTask.id
  }
}

async function loadQuestion(): Promise<void> {
  const id = questionId.value

  resetTaskPolling()
  handledDoneTaskIds.clear()
  knownQuizTaskId = 0
  generationRequested.value = false
  generationMode.value = 'legacy'
  retryingTaskId.value = null
  refreshQueued.value = false

  if (id === null) {
    loading.value = false
    notFound.value = true
    errorMessage.value = ''
    question.value = null
    return
  }

  const token = ++loadToken
  loading.value = true
  notFound.value = false
  errorMessage.value = ''
  errorCode.value = ''
  actionError.value = ''

  try {
    const detail = await getQuestion(id, { includeGenerated: true })
    if (token !== loadToken) return

    question.value = detail
    generationMode.value = detail.tasks.some(isSegmentTask) ? 'segments' : 'legacy'
    setPollingTasks(detail.tasks)
    rememberLatestQuizTask(detail.tasks)
    for (const task of detail.tasks) {
      if (task.status === 'done') handledDoneTaskIds.add(task.id)
    }

    if (hasActiveTasks(detail.tasks)) startTaskPolling()
  } catch (cause) {
    if (token !== loadToken) return

    const apiError = normalizeApiError(cause)
    if (apiError.status === 404) {
      notFound.value = true
      question.value = null
    } else {
      errorMessage.value = apiError.message
      errorCode.value = apiError.code
      question.value = null
    }
  } finally {
    if (token === loadToken) loading.value = false
  }
}

async function refreshQuestion(options: { silent?: boolean } = {}): Promise<void> {
  const current = question.value
  if (!current) return
  if (refreshing.value) {
    refreshQueued.value = true
    return
  }

  const token = loadToken
  refreshing.value = true
  if (!options.silent) actionError.value = ''

  try {
    const detail = await getQuestion(current.id, { includeGenerated: true })
    if (token !== loadToken) return

    question.value = detail
    if (detail.tasks.some(isSegmentTask)) generationMode.value = 'segments'
    generationRequested.value = false
    rememberLatestQuizTask(detail.tasks)

    for (const task of detail.tasks) {
      if (task.status === 'done') handledDoneTaskIds.add(task.id)
    }
  } catch (cause) {
    if (token === loadToken) actionError.value = normalizeApiError(cause).message
  } finally {
    refreshing.value = false
    if (token !== loadToken) {
      refreshQueued.value = false
    } else if (refreshQueued.value) {
      refreshQueued.value = false
      void refreshQuestion({ silent: true })
    }
  }
}

async function handleGenerate(): Promise<void> {
  const current = question.value
  if (!current || submittingGeneration.value || generationBusy.value) return

  submittingGeneration.value = true
  actionError.value = ''

  try {
    const result = await generateQuestions(current.id)
    const hasSegmentTargets = result.tasks.some((task) => task.target_index !== null)

    generationMode.value = hasSegmentTargets ? 'segments' : 'legacy'
    generationRequested.value = true
    if (hasSegmentTargets) current.generated_questions = []
    startTaskPolling()

    const legacyTask = result.tasks[0]
    Message.success({
      content: hasSegmentTargets
        ? `已提交 ${result.tasks.length} 个并发生成任务，完成后会自动展示相似题。`
        : `已提交生成任务（#${legacyTask.task_id}），完成后会自动展示相似题。`,
      duration: 4000,
    })
  } catch (cause) {
    actionError.value = normalizeApiError(cause).message
  } finally {
    submittingGeneration.value = false
  }
}

async function handleRetryTask(taskId: number): Promise<void> {
  if (retryingTaskId.value !== null) return

  retryingTaskId.value = taskId
  actionError.value = ''

  try {
    await retryTask(taskId)
    Message.success(`任务 #${taskId} 已重新提交`)
    startTaskPolling()
  } catch (cause) {
    actionError.value = normalizeApiError(cause).message
  } finally {
    retryingTaskId.value = null
  }
}

async function handleRefreshTasks(): Promise<void> {
  const result = await refreshTasks()
  if (result === null) return

  if (!hasActiveTasks(result)) {
    await refreshQuestion({ silent: true })
  }
}

function handleRefreshQuestion(): void {
  void refreshQuestion()
}

async function handleDelete(): Promise<boolean> {
  const current = question.value
  if (!current || deleting.value) return false

  deleting.value = true
  deleteError.value = ''

  try {
    await removeQuestion(current.id)
    Message.success('错题已删除')
    deleteDialogVisible.value = false
    await router.replace('/questions')
    return true
  } catch (cause) {
    deleteError.value = normalizeApiError(cause).message
    return false
  } finally {
    deleting.value = false
  }
}

function openDeleteDialog(): void {
  deleteError.value = ''
  deleteDialogVisible.value = true
}

function goPractice(): void {
  if (!question.value) return
  void router.push(`/practice/${question.value.id}`)
}

function goEdit(): void {
  if (!question.value) return
  void router.push(`/questions/${question.value.id}/edit`)
}

watch(
  () => liveTasks.value,
  (next) => {
    let shouldRefreshQuestion = false

    for (const task of next) {
      if (task.status !== 'done' || handledDoneTaskIds.has(task.id)) continue

      handledDoneTaskIds.add(task.id)
      shouldRefreshQuestion = true
    }

    const latestQuizTask = latestTask(next, 'quiz')
    if (latestQuizTask && latestQuizTask.id > knownQuizTaskId) {
      knownQuizTaskId = latestQuizTask.id
      generationRequested.value = false
    }

    if (shouldRefreshQuestion) void refreshQuestion({ silent: true })
  },
)

watch(questionId, () => void loadQuestion(), { immediate: true })

onBeforeUnmount(() => {
  loadToken += 1
})
</script>

<template>
  <div class="page">
    <LoadingSkeleton v-if="loading" variant="detail" label="正在加载错题详情" />

    <EmptyState
      v-else-if="notFound"
      title="错题不存在或已删除"
      description="这道错题可能已被删除，或链接中的编号不正确。"
      action-label="返回错题本"
      @action="router.push('/questions')"
    />

    <ErrorState
      v-else-if="errorMessage"
      title="错题详情加载失败"
      :message="errorMessage"
      :code="errorCode"
      @retry="loadQuestion"
    />

    <template v-else-if="question">
      <header class="page-head">
        <div class="page-head__copy">
          <a class="backlink" href="/questions" @click.prevent="router.push('/questions')">
            <IconArrowLeft class="icon" />
            返回错题本
          </a>
          <h1>
            错题详情
            <span class="head-id">#{{ question.id }}</span>
          </h1>
          <p>{{ detailSubtitle }}</p>
        </div>
        <div class="page-head__actions">
          <span class="tag" :class="masteryTagClass">
            <span class="dot" aria-hidden="true" />
            {{ masteryStatusLabel(question.mastery_status) }}
          </span>
          <button class="btn btn--outline" type="button" @click="goEdit">
            <IconEdit class="icon" />
            编辑
          </button>
          <button class="btn btn--danger" type="button" @click="openDeleteDialog">
            <IconDelete class="icon" />
            删除
          </button>
        </div>
      </header>

      <div class="detail-layout">
        <div class="detail-main">
          <article class="paper" aria-labelledby="original-title">
            <div class="paper__head">
              <h2 id="original-title">原题</h2>
              <span class="paper__meta">
                {{ questionTypeLabel(question.question_type) }} ·
                {{ question.source_type === 'image' ? '图片录入' : '文字录入' }}
              </span>
            </div>
            <div class="paper__body">
              <div class="question-stem">
                <MarkdownRenderer :content="question.content_md" />
              </div>

              <ol v-if="question.options?.length" class="question-options">
                <li
                  v-for="option in question.options"
                  :key="option.label"
                  class="question-options__item"
                >
                  <span class="question-options__label">{{ option.label }}</span>
                  <MarkdownRenderer :content="option.content_md" compact />
                </li>
              </ol>
            </div>

            <div v-if="hasAnyQa" class="answer-stack">
              <details v-if="hasAnswerContent" class="collapse">
                <summary>
                  <svg
                    class="chev"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.8"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                  >
                    <path d="m9 6 6 6-6 6" />
                  </svg>
                  答案
                  <span class="collapse__state" aria-hidden="true" />
                </summary>
                <div class="collapse__body">
                  <MarkdownRenderer v-if="hasAnswer" :content="question.answer_md ?? ''" />
                  <ul v-if="blanks.length" class="question-blanks">
                    <li v-for="blank in blanks" :key="blank.index" class="question-blanks__item">
                      <span class="question-blanks__label">第 {{ blank.index }} 空</span>
                      <MarkdownRenderer :content="blank.answer_md" compact />
                    </li>
                  </ul>
                </div>
              </details>

              <details v-if="hasExplanation" class="collapse">
                <summary>
                  <svg
                    class="chev"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.8"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                  >
                    <path d="m9 6 6 6-6 6" />
                  </svg>
                  解析
                  <span class="collapse__state" aria-hidden="true" />
                </summary>
                <div class="collapse__body">
                  <MarkdownRenderer :content="question.explanation_md ?? ''" />
                </div>
              </details>
            </div>

            <div v-else class="answer-empty">
              <p class="hint">暂无答案与解析，AI 分析任务完成后会自动补全。</p>
            </div>
          </article>

          <AnalysisCard
            :analysis="question.analysis"
            :pending="analysisPending"
            :failed="analysisFailed"
            :task-label="analysisTaskLabel"
          />

          <section class="generated" aria-labelledby="generated-title">
            <div class="subhead">
              <h2 id="generated-title">相似题</h2>
              <span class="count">{{ generatedCount }} / 3</span>
              <div class="subhead__tools">
                <span v-if="allGeneratedValid" class="subhead__right">
                  <svg
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
                  均通过结构校验
                </span>
                <button
                  class="btn btn--quiet btn--sm subhead__refresh"
                  type="button"
                  :disabled="refreshing"
                  @click="handleRefreshQuestion"
                >
                  <IconRefresh class="icon" />
                  {{ refreshing ? '刷新中…' : '刷新' }}
                </button>
              </div>
            </div>

            <div v-if="generatedCount > 0" class="gen-list">
              <GeneratedQuestionCard
                v-for="(item, index) in sortedGeneratedQuestions"
                :key="item.id"
                :question="item"
                :index="item.target_index ?? index + 1"
              />
            </div>

            <div v-else class="paper empty-note">
              <p class="empty-note__title">还没有生成题</p>
              <p class="empty-note__text">{{ generatedEmptyHint }}</p>
            </div>
          </section>
        </div>

        <aside class="detail-aside" aria-label="处理进度">
          <GenerationSegments
            v-if="generationMode === 'segments'"
            :tasks="liveTasks"
            :polling="isPolling"
            :loading="tasksLoading"
            :timed-out="pollingTimedOut"
            :stopped="pollingStopped"
            :error-message="pollingError?.message ?? ''"
            :error-code="pollingError?.code ?? ''"
            :generated-count="generatedCount"
            :analysis-ready="analysisReady"
            :generation-requested="generationRequested"
            :retrying-task-id="retryingTaskId"
            @retry="handleRetryTask"
            @stop="stopTaskPolling"
            @refresh="handleRefreshTasks"
            @generate="handleGenerate"
            @practice="goPractice"
          />

          <GenerationProgress
            v-else
            :tasks="legacyTasks"
            :polling="isPolling"
            :loading="tasksLoading"
            :timed-out="pollingTimedOut"
            :stopped="pollingStopped"
            :error-message="pollingError?.message ?? ''"
            :error-code="pollingError?.code ?? ''"
            :generated-count="generatedCount"
            :analysis-ready="analysisReady"
            :generation-requested="generationRequested"
            :retrying-task-id="retryingTaskId"
            @retry="handleRetryTask"
            @stop="stopTaskPolling"
            @refresh="handleRefreshTasks"
            @generate="handleGenerate"
            @practice="goPractice"
          />

          <p v-if="actionError" class="aside-error" role="alert">{{ actionError }}</p>
        </aside>
      </div>
    </template>

    <a-modal
      v-model:visible="deleteDialogVisible"
      title="删除这道错题？"
      ok-text="删除"
      cancel-text="取消"
      :ok-loading="deleting"
      :ok-button-props="{ status: 'danger' }"
      :cancel-button-props="{ disabled: deleting }"
      :mask-closable="!deleting"
      :closable="!deleting"
      :on-before-ok="handleDelete"
    >
      <p class="delete-dialog__text">
        删除后，原题、AI 分析、生成题与关联任务都会移除，且不可恢复。
      </p>
      <a-alert v-if="deleteError" type="error" show-icon>{{ deleteError }}</a-alert>
    </a-modal>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-6);
}

.page-head__copy {
  min-width: 0;
}

.backlink {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 6px;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.backlink:hover {
  color: var(--color-primary-active);
}

.backlink .icon {
  width: 15px;
  height: 15px;
}

.page-head h1 {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 10px;
  font-size: var(--text-2xl);
  line-height: var(--text-2xl-leading);
  font-weight: 650;
  letter-spacing: -0.012em;
}

.head-id {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 400;
  letter-spacing: 0.02em;
}

.page-head p {
  max-width: 680px;
  margin-top: 4px;
  color: var(--color-text-2);
  font-size: 15px;
  line-height: 24px;
  text-wrap: pretty;
}

.page-head__actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  grid-template-areas: 'main aside';
  align-items: start;
  gap: var(--space-5);
}

.detail-main {
  grid-area: main;
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  min-width: 0;
}

.detail-aside {
  grid-area: aside;
  position: sticky;
  top: 20px;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.aside-error {
  padding: 10px var(--space-3);
  border: 1px solid var(--color-danger-border);
  border-radius: var(--radius-md);
  background: var(--color-danger-soft);
  color: var(--color-danger-text);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.question-stem {
  max-width: 46em;
  font-size: var(--text-base);
  line-height: var(--text-base-leading);
  font-weight: 500;
  color: var(--color-text-1);
  text-wrap: pretty;
}

.question-stem :deep(.markdown-renderer) {
  font-weight: 500;
}

.question-stem :deep(.markdown-renderer p) {
  margin-bottom: var(--space-2);
}

.question-stem :deep(.markdown-renderer > :last-child) {
  margin-bottom: 0;
}

.question-options {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: var(--space-4) 0 0;
  padding: 0;
  list-style: none;
}

.question-options__item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  min-width: 0;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.question-options__label {
  flex: none;
  min-width: 1.5em;
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 600;
  line-height: var(--text-sm-leading);
}

.answer-stack {
  border-top: 1px solid var(--color-border);
}

.answer-stack .collapse {
  padding: 0 var(--space-6);
}

.answer-stack .collapse + .collapse {
  border-top: 1px solid var(--color-border);
}

.question-blanks {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: var(--space-3) 0 0;
  padding: 0;
  list-style: none;
}

.question-blanks__item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  min-width: 0;
}

.question-blanks__label {
  flex: none;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-base-leading);
}

.answer-empty {
  padding: 12px var(--space-6) var(--space-6);
  border-top: 1px solid var(--color-border);
}

.answer-empty .hint {
  margin: 0;
}

.subhead {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 10px;
  margin-bottom: 10px;
}

.subhead h2 {
  font-size: var(--text-lg);
  line-height: var(--text-lg-leading);
  font-weight: 650;
}

.subhead .count {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.subhead__tools {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-left: auto;
}

.subhead__right {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--color-success);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.subhead__right .icon {
  width: 14px;
  height: 14px;
}

.subhead__refresh {
  min-height: 30px;
  margin-left: auto;
  padding: 0 var(--space-2);
}

.gen-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.empty-note {
  padding: var(--space-5) var(--space-6);
}

.empty-note__title {
  color: var(--color-text-1);
  font-size: var(--text-base);
  line-height: 24px;
  font-weight: 650;
}

.empty-note__text {
  margin-top: var(--space-1);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.delete-dialog__text {
  margin-bottom: var(--space-3);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

@media (max-width: 1024px) {
  .detail-layout {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas: 'aside' 'main';
  }

  .detail-aside {
    position: static;
  }
}

@media (max-width: 767px) {
  .page {
    gap: var(--space-4);
  }

  .page-head {
    gap: var(--space-3);
  }

  .page-head h1 {
    font-size: 24px;
    line-height: 32px;
  }

  .page-head p {
    font-size: var(--text-sm);
    line-height: var(--text-sm-leading);
  }

  .page-head__actions {
    width: auto;
    margin-left: auto;
  }

  .paper__head {
    padding: 12px var(--space-4);
  }

  .paper__body {
    padding: var(--space-4);
  }

  .answer-stack .collapse {
    padding: 0 var(--space-4);
  }

  .answer-empty {
    padding: 12px var(--space-4) var(--space-4);
  }

  .subhead__tools {
    width: 100%;
    margin-left: 0;
    justify-content: space-between;
  }

  .empty-note {
    padding: var(--space-4);
  }
}
</style>
