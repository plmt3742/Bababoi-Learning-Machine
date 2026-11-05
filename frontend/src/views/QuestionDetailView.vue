<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconArrowLeft, IconDelete, IconRefresh } from '@arco-design/web-vue/es/icon'
import '@arco-design/web-vue/es/message/style/css.js'
import PageHeader from '../components/common/PageHeader.vue'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import LoadingSkeleton from '../components/common/LoadingSkeleton.vue'
import MarkdownRenderer from '../components/common/MarkdownRenderer.vue'
import AnalysisCard from '../components/question/AnalysisCard.vue'
import GeneratedQuestionCard from '../components/question/GeneratedQuestionCard.vue'
import { generateQuestions, getQuestion, removeQuestion } from '../api/questions'
import { normalizeApiError } from '../api/errors'
import type { QuestionDetail } from '../api/types'
import {
  formatDateTime,
  masteryStatusColor,
  masteryStatusLabel,
  questionTypeLabel,
} from '../utils/question'

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
const generating = ref(false)
const refreshing = ref(false)
const generationRequested = ref(false)
const actionError = ref('')

let loadToken = 0

const questionId = computed<number | null>(() => {
  const raw = route.params.id
  const value = Array.isArray(raw) ? raw[0] : raw
  if (!value) return null

  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) && parsed > 0 && String(parsed) === value ? parsed : null
})

const pageDescription = computed(() => {
  if (!question.value) return '查看原题、AI 分析与 3 道相似题。'

  const parts = [question.value.subject]
  if (question.value.chapter) parts.push(question.value.chapter)
  return parts.join(' · ')
})

const createdAt = computed(() => (question.value ? formatDateTime(question.value.created_at) : ''))
const hasAnswer = computed(() => Boolean(question.value?.answer_md?.trim()))
const hasExplanation = computed(() => Boolean(question.value?.explanation_md?.trim()))
const blanks = computed(() => question.value?.blanks ?? [])
const generatedCount = computed(() => question.value?.generated_questions.length ?? 0)

const analysisTask = computed(
  () => question.value?.tasks.find((task) => task.stage === 'analysis') ?? null,
)
const analysisPending = computed(
  () =>
    !question.value?.analysis &&
    (analysisTask.value?.status === 'queued' || analysisTask.value?.status === 'running'),
)
const analysisFailed = computed(
  () => !question.value?.analysis && analysisTask.value?.status === 'failed',
)

const generatedStatus = computed<'ready' | 'analysis-pending' | 'generating' | 'empty'>(() => {
  if (generatedCount.value > 0) return 'ready'
  if (analysisPending.value) return 'analysis-pending'
  if (generationRequested.value) return 'generating'

  const quizRunning = (question.value?.tasks ?? []).some(
    (task) => task.stage === 'quiz' && (task.status === 'queued' || task.status === 'running'),
  )

  return quizRunning ? 'generating' : 'empty'
})

async function loadQuestion(): Promise<void> {
  const id = questionId.value

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

async function refreshQuestion(): Promise<void> {
  const current = question.value
  if (!current || refreshing.value) return

  refreshing.value = true
  actionError.value = ''

  try {
    question.value = await getQuestion(current.id, { includeGenerated: true })
    generationRequested.value = false
  } catch (cause) {
    actionError.value = normalizeApiError(cause).message
  } finally {
    refreshing.value = false
  }
}

async function handleGenerate(): Promise<void> {
  const current = question.value
  if (!current || generating.value) return

  generating.value = true
  actionError.value = ''

  try {
    const result = await generateQuestions(current.id)
    generationRequested.value = true
    Message.success({
      content: `已提交生成任务（#${result.task_id}），完成后点击“刷新状态”查看相似题。`,
      duration: 4500,
    })
  } catch (cause) {
    actionError.value = normalizeApiError(cause).message
  } finally {
    generating.value = false
  }
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

watch(questionId, () => void loadQuestion(), { immediate: true })

onBeforeUnmount(() => {
  loadToken += 1
})
</script>

<template>
  <div class="page">
    <PageHeader eyebrow="QDETAIL-01" title="错题详情" :description="pageDescription">
      <template #actions>
        <a-button @click="router.push('/questions')">
          <template #icon>
            <IconArrowLeft />
          </template>
          返回错题本
        </a-button>
        <a-button v-if="question" status="danger" type="outline" @click="openDeleteDialog">
          <template #icon>
            <IconDelete />
          </template>
          删除
        </a-button>
      </template>
    </PageHeader>

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
      <div class="detail-stack">
        <section class="detail-section" aria-labelledby="question-original-heading">
          <div class="section-heading">
            <h2 id="question-original-heading" class="section-heading__title">原题</h2>
            <span class="section-heading__meta">
              {{ questionTypeLabel(question.question_type) }}
            </span>
          </div>

          <a-card class="question-card" :bordered="false">
            <div class="question-card__meta">
              <a-tag size="small" :color="masteryStatusColor(question.mastery_status)">
                {{ masteryStatusLabel(question.mastery_status) }}
              </a-tag>
              <span>录入于 {{ createdAt }}</span>
            </div>

            <MarkdownRenderer :content="question.content_md" />

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

            <a-collapse
              v-if="hasAnswer || hasExplanation || blanks.length"
              class="answer-collapse"
              :bordered="false"
            >
              <a-collapse-item v-if="hasAnswer || blanks.length" key="answer" header="答案">
                <MarkdownRenderer v-if="hasAnswer" :content="question.answer_md ?? ''" compact />
                <ul v-if="blanks.length" class="question-blanks">
                  <li v-for="blank in blanks" :key="blank.index" class="question-blanks__item">
                    <span class="question-blanks__label">第 {{ blank.index }} 空</span>
                    <MarkdownRenderer :content="blank.answer_md" compact />
                  </li>
                </ul>
              </a-collapse-item>
              <a-collapse-item v-if="hasExplanation" key="explanation" header="解析">
                <MarkdownRenderer :content="question.explanation_md ?? ''" compact />
              </a-collapse-item>
            </a-collapse>

            <a-alert v-else type="info" :show-icon="true">
              暂无答案与解析，AI 分析任务完成后会自动补全。
            </a-alert>
          </a-card>
        </section>

        <AnalysisCard
          :analysis="question.analysis"
          :pending="analysisPending"
          :failed="analysisFailed"
        />

        <section class="detail-section" aria-labelledby="question-generated-heading">
          <div class="section-heading">
            <h2 id="question-generated-heading" class="section-heading__title">
              生成题
              <span v-if="generatedCount > 0" class="section-heading__count">
                {{ generatedCount }}/3
              </span>
            </h2>
            <a-button size="small" type="text" :loading="refreshing" @click="refreshQuestion">
              <template #icon>
                <IconRefresh />
              </template>
              刷新状态
            </a-button>
          </div>

          <a-alert v-if="generatedStatus === 'analysis-pending'" type="info" :show-icon="true">
            AI 分析任务还在进行，完成后即可基于分析结果生成 3 道相似题。
          </a-alert>

          <a-alert v-else-if="generatedStatus === 'generating'" type="info" :show-icon="true">
            相似题生成任务已提交，完成后点击「刷新状态」即可查看。
          </a-alert>

          <div v-if="generatedCount > 0" class="generated-list">
            <GeneratedQuestionCard
              v-for="(item, index) in question.generated_questions"
              :key="item.id"
              :question="item"
              :index="index + 1"
            />
          </div>

          <div v-else-if="generatedStatus === 'empty'" class="generated-empty">
            <EmptyState
              title="还没有生成题"
              description="生成后会在这里按 1–3 展示相似题，答案与解析默认折叠。"
              action-label="生成相似题"
              @action="handleGenerate"
            />
          </div>
        </section>

        <section class="detail-actions" aria-labelledby="question-actions-heading">
          <div class="detail-actions__copy">
            <h2 id="question-actions-heading" class="section-heading__title">下一步</h2>
            <p class="detail-actions__hint">去练习用相似题自测，或继续补全这道题的生成结果。</p>
          </div>

          <a-alert v-if="actionError" type="error" show-icon closable @close="actionError = ''">
            {{ actionError }}
          </a-alert>

          <div class="detail-actions__buttons">
            <a-button
              type="primary"
              :loading="generating"
              :disabled="generating"
              @click="handleGenerate"
            >
              生成相似题
            </a-button>
            <a-button @click="goPractice">去练习</a-button>
          </div>
        </section>
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

.detail-stack {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.section-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.section-heading__title {
  font-size: var(--text-lg);
  line-height: var(--text-lg-leading);
}

.section-heading__count {
  margin-left: var(--space-1);
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 500;
}

.section-heading__meta {
  color: var(--color-text-3);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
}

.question-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.question-card :deep(.arco-card-body) {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-5);
}

.question-card__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-3);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
}

.question-options {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.question-options__item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.question-options__label {
  min-width: 1.5em;
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 600;
  line-height: var(--text-sm-leading);
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
}

.question-blanks__label {
  flex: none;
  color: var(--color-text-3);
  font-size: var(--text-xs);
  line-height: var(--text-sm-leading);
}

.answer-collapse {
  border-top: 1px solid var(--color-border);
}

.answer-collapse :deep(.arco-collapse-item) {
  border-bottom: 0;
}

.answer-collapse :deep(.arco-collapse-item-header) {
  padding-right: 0;
  padding-left: 0;
  border-bottom: 0;
  background: transparent;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  font-weight: 500;
}

.answer-collapse :deep(.arco-collapse-item-content) {
  background: transparent;
}

.answer-collapse :deep(.arco-collapse-item-content-box) {
  padding: var(--space-2) 0 0;
}

.generated-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.generated-empty,
.detail-actions {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.detail-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5);
}

.detail-actions__copy {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.detail-actions__hint {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.detail-actions__buttons {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.delete-dialog__text {
  margin-bottom: var(--space-3);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

@media (max-width: 767px) {
  .question-card :deep(.arco-card-body) {
    padding: var(--space-4);
  }

  .detail-actions {
    padding: var(--space-4);
  }

  .detail-actions__buttons :deep(.arco-btn) {
    flex: 1 1 auto;
  }
}
</style>
