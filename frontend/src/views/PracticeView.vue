<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import LoadingSkeleton from '../components/common/LoadingSkeleton.vue'
import PageHeader from '../components/common/PageHeader.vue'
import PracticeQuestionCard from '../components/practice/PracticeQuestionCard.vue'
import PracticeResultPanel from '../components/practice/PracticeResultPanel.vue'
import { normalizeApiError } from '../api/errors'
import { createPracticeRecord } from '../api/practice'
import { getQuestion, updateQuestion } from '../api/questions'
import type { GeneratedQuestion, MasteryStatus, QuestionDetail } from '../api/types'
import {
  formatPracticeClock,
  masteryStatusForResults,
  parsePracticeId,
  type PracticeResultItem,
} from '../utils/practice'

const route = useRoute()
const router = useRouter()

const question = ref<QuestionDetail | null>(null)
const loading = ref(true)
const notFound = ref(false)
const errorMessage = ref('')
const errorCode = ref('')

const currentIndex = ref(0)
const results = ref<PracticeResultItem[]>([])
const finished = ref(false)
const submitting = ref(false)
const submitError = ref('')
const lastGrade = ref<boolean | null>(null)
const lastUserAnswer = ref<string | null>(null)

const masteryStatus = ref<MasteryStatus | null>(null)
const masterySyncing = ref(false)
const masteryError = ref('')
const masterySynced = ref(false)

const elapsedSeconds = ref(0)
let timerId: number | null = null
let questionStartedAt = 0
let loadToken = 0
let masteryToken = 0

const rawQuestionId = computed<string>(() => {
  const raw: string | string[] | undefined = route.params.id
  if (Array.isArray(raw)) return raw[0] ?? ''
  return raw ?? ''
})

const hasQuestionParam = computed(() => rawQuestionId.value.length > 0)
const parentQuestionId = computed(() => parsePracticeId(rawQuestionId.value))
const practiceQuestions = computed<GeneratedQuestion[]>(() => {
  const items = question.value?.generated_questions ?? []
  return items.filter((item) => item.content_md.trim().length > 0)
})
const currentQuestion = computed<GeneratedQuestion | null>(() => {
  if (finished.value) return null
  return practiceQuestions.value.at(currentIndex.value) ?? null
})
const totalQuestions = computed(() => practiceQuestions.value.length)
const elapsedLabel = computed(() => formatPracticeClock(elapsedSeconds.value))

function stopTimer(): void {
  if (timerId !== null) {
    window.clearInterval(timerId)
    timerId = null
  }
}

function startTimer(): void {
  stopTimer()
  questionStartedAt = Date.now()
  elapsedSeconds.value = 0
  timerId = window.setInterval(() => {
    elapsedSeconds.value = Math.min(3600, Math.floor((Date.now() - questionStartedAt) / 1000))
  }, 1000)
}

function readElapsedSeconds(): number {
  if (questionStartedAt <= 0) return 0
  return Math.max(0, Math.min(3600, Math.floor((Date.now() - questionStartedAt) / 1000)))
}

function resetSession(): void {
  masteryToken += 1
  currentIndex.value = 0
  results.value = []
  finished.value = false
  submitting.value = false
  submitError.value = ''
  lastGrade.value = null
  lastUserAnswer.value = null
  masteryStatus.value = null
  masterySyncing.value = false
  masteryError.value = ''
  masterySynced.value = false
  stopTimer()
  questionStartedAt = 0
  elapsedSeconds.value = 0
}

async function loadPractice(): Promise<void> {
  const id = parentQuestionId.value
  const token = ++loadToken

  question.value = null
  resetSession()
  loading.value = true
  notFound.value = false
  errorMessage.value = ''
  errorCode.value = ''

  if (id === null) {
    loading.value = false
    notFound.value = hasQuestionParam.value
    return
  }

  try {
    const detail = await getQuestion(id, { includeGenerated: true })
    if (token !== loadToken) return
    question.value = detail
  } catch (cause) {
    if (token !== loadToken) return

    const apiError = normalizeApiError(cause)
    if (apiError.status === 404) {
      notFound.value = true
    } else {
      errorMessage.value = apiError.message
      errorCode.value = apiError.code
    }
  } finally {
    if (token === loadToken) loading.value = false
  }
}

async function syncMastery(): Promise<void> {
  const id = parentQuestionId.value
  if (id === null || results.value.length === 0 || masterySyncing.value) return

  const token = ++masteryToken
  masterySyncing.value = true
  masteryError.value = ''

  try {
    const nextStatus = masteryStatusForResults(results.value)
    const updated = await updateQuestion(id, { mastery_status: nextStatus })
    if (token !== masteryToken) return

    masteryStatus.value = updated.mastery_status
    masterySynced.value = true
    if (question.value) {
      question.value = { ...question.value, mastery_status: updated.mastery_status }
    }
  } catch (cause) {
    if (token !== masteryToken) return

    masteryError.value = normalizeApiError(cause).message
    masterySynced.value = false
  } finally {
    if (token === masteryToken) masterySyncing.value = false
  }
}

function recordAndAdvance(
  generatedQuestionId: number,
  userAnswer: string | null,
  isCorrect: boolean,
  durationSeconds: number,
): void {
  results.value = [
    ...results.value,
    {
      generated_question_id: generatedQuestionId,
      user_answer: userAnswer,
      is_correct: isCorrect,
      duration_seconds: durationSeconds,
    },
  ]

  if (currentIndex.value + 1 >= practiceQuestions.value.length) {
    finished.value = true
    stopTimer()
    void syncMastery()
    return
  }

  currentIndex.value += 1
}

async function handleGrade(isCorrect: boolean, userAnswer: string | null): Promise<void> {
  const current = currentQuestion.value
  if (!current || submitting.value || finished.value) return

  submitting.value = true
  submitError.value = ''
  lastGrade.value = isCorrect
  lastUserAnswer.value = userAnswer

  const durationSeconds = readElapsedSeconds()

  try {
    await createPracticeRecord({
      generated_question_id: current.id,
      user_answer: userAnswer,
      is_correct: isCorrect,
      duration_seconds: durationSeconds,
    })
    recordAndAdvance(current.id, userAnswer, isCorrect, durationSeconds)
  } catch (cause) {
    const apiError = normalizeApiError(cause)
    // A retried request whose first response was lost is already recorded.
    if (apiError.code === 'PRACTICE_DUPLICATE') {
      recordAndAdvance(current.id, userAnswer, isCorrect, durationSeconds)
    } else {
      submitError.value = apiError.message
    }
  } finally {
    submitting.value = false
  }
}

function retrySubmit(): void {
  if (lastGrade.value === null || submitting.value) return
  void handleGrade(lastGrade.value, lastUserAnswer.value)
}

function restartPractice(): void {
  masteryToken += 1
  results.value = []
  currentIndex.value = 0
  finished.value = false
  submitting.value = false
  submitError.value = ''
  lastGrade.value = null
  lastUserAnswer.value = null
  masteryStatus.value = null
  masterySyncing.value = false
  masteryError.value = ''
  masterySynced.value = false
  stopTimer()
  questionStartedAt = 0
  elapsedSeconds.value = 0
  window.scrollTo({ top: 0 })
}

function segmentClass(index: number): string {
  const result = results.value.at(index)
  if (result) return result.is_correct ? 'is-correct' : 'is-wrong'
  if (!finished.value && index === currentIndex.value) return 'is-current'
  return ''
}

function goQuestionList(): void {
  void router.push('/questions')
}

function goQuestionDetail(): void {
  const id = parentQuestionId.value
  if (id === null) {
    goQuestionList()
    return
  }
  void router.push(`/questions/${id}`)
}

function goStats(): void {
  void router.push('/stats')
}

watch(
  currentQuestion,
  (next) => {
    submitError.value = ''
    lastGrade.value = null
    lastUserAnswer.value = null

    if (next) startTimer()
    else stopTimer()
  },
  { immediate: true },
)

watch(rawQuestionId, () => void loadPractice(), { immediate: true })

onBeforeUnmount(() => {
  loadToken += 1
  masteryToken += 1
  stopTimer()
})
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="Practice"
      title="练习"
      description="逐题作答、查看答案后自评；每题用时自动记录，提交后进入下一题。"
    >
      <template #actions>
        <div v-if="!loading && !finished && currentQuestion" class="session-meta">
          <span class="session-meta__progress">
            第 {{ currentIndex + 1 }} / {{ totalQuestions }} 题
          </span>
          <span class="session-meta__timer" role="timer" aria-label="本题已用时">
            <svg
              class="icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="8.5" />
              <path d="M12 7.5V12l3 1.8" />
            </svg>
            {{ elapsedLabel }}
          </span>
        </div>
        <span v-else-if="finished" class="tag tag--ok">
          <span class="dot" aria-hidden="true" />
          本轮 {{ results.length }} 题已完成
        </span>
      </template>
    </PageHeader>

    <LoadingSkeleton v-if="loading" variant="detail" label="正在加载练习题" />

    <div v-else-if="!hasQuestionParam" class="state-stack">
      <EmptyState
        title="从一道错题开始练习"
        description="练习会依次呈现该错题的相似题。打开错题详情，点击「去练习」即可开始。"
        action-label="去错题本"
        @action="goQuestionList"
      />

      <section class="paper entry-guide" aria-labelledby="practice-guide-title">
        <div class="paper__head">
          <h2 id="practice-guide-title">练习流程</h2>
          <span class="paper__meta">一道题约 1–3 分钟</span>
        </div>
        <ol class="entry-guide__list">
          <li class="entry-guide__item">
            <span class="entry-guide__no" aria-hidden="true">01</span>
            <div class="entry-guide__copy">
              <p class="entry-guide__title">打开一道错题</p>
              <p class="entry-guide__text">在错题本中选择要巩固的题目，查看 AI 分析与原题。</p>
            </div>
          </li>
          <li class="entry-guide__item">
            <span class="entry-guide__no" aria-hidden="true">02</span>
            <div class="entry-guide__copy">
              <p class="entry-guide__title">准备相似题</p>
              <p class="entry-guide__text">如果还没有生成题，先在详情页生成 3 道相似题。</p>
            </div>
          </li>
          <li class="entry-guide__item">
            <span class="entry-guide__no" aria-hidden="true">03</span>
            <div class="entry-guide__copy">
              <p class="entry-guide__title">开始逐题练习</p>
              <p class="entry-guide__text">作答、查看答案并自评「会 / 不会」，记录自动保存。</p>
            </div>
          </li>
        </ol>
      </section>
    </div>

    <EmptyState
      v-else-if="notFound"
      title="错题不存在或已删除"
      description="这道错题可能已被删除，或链接中的编号不正确。"
      action-label="返回错题本"
      @action="goQuestionList"
    />

    <ErrorState
      v-else-if="errorMessage"
      title="练习题加载失败"
      :message="errorMessage"
      :code="errorCode"
      @retry="loadPractice"
    />

    <EmptyState
      v-else-if="practiceQuestions.length === 0"
      title="还没有可练习的相似题"
      description="先为这道错题生成相似题，完成后就能在这里逐题练习。"
      action-label="返回错题详情"
      @action="goQuestionDetail"
    />

    <PracticeResultPanel
      v-else-if="finished"
      :results="results"
      :questions="practiceQuestions"
      :mastery-status="masteryStatus"
      :mastery-syncing="masterySyncing"
      :mastery-error="masteryError"
      :mastery-synced="masterySynced"
      @restart="restartPractice"
      @back="goQuestionDetail"
      @stats="goStats"
      @retry-sync="syncMastery"
    />

    <div v-else-if="currentQuestion" class="practice-shell">
      <div class="progress-rail" aria-hidden="true">
        <span
          v-for="(item, index) in practiceQuestions"
          :key="item.id"
          class="progress-rail__seg"
          :class="segmentClass(index)"
        />
      </div>

      <PracticeQuestionCard
        :key="currentQuestion.id"
        :question="currentQuestion"
        :index="currentIndex"
        :total="totalQuestions"
        :submitting="submitting"
        :submit-error="submitError"
        @grade="handleGrade"
        @retry="retrySubmit"
      />
    </div>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
}

.session-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.session-meta__progress {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: 1;
  font-weight: 600;
}

.session-meta__timer {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-subtle);
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.session-meta__timer .icon {
  width: 15px;
  height: 15px;
  flex: none;
  color: var(--color-text-3);
}

.state-stack {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.practice-shell {
  width: 100%;
  max-width: 820px;
  margin: 0 auto;
  min-width: 0;
}

.progress-rail {
  display: flex;
  gap: 4px;
  margin-bottom: var(--space-3);
}

.progress-rail__seg {
  flex: 1 1 0;
  height: 4px;
  border-radius: 999px;
  background: var(--color-page-deep);
  transition: background-color 0.15s ease;
}

.progress-rail__seg.is-current {
  background: var(--color-primary-border);
}

.progress-rail__seg.is-correct {
  background: var(--color-success);
}

.progress-rail__seg.is-wrong {
  background: var(--color-danger);
}

.entry-guide {
  overflow: hidden;
}

.entry-guide__list {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
}

.entry-guide__item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.entry-guide__item:last-child {
  border-bottom: 0;
}

.entry-guide__no {
  flex: none;
  color: var(--color-primary-active);
  font-family: var(--font-math);
  font-size: 22px;
  line-height: 1;
}

.entry-guide__copy {
  min-width: 0;
}

.entry-guide__title {
  color: var(--color-text-1);
  font-size: var(--text-base);
  line-height: 24px;
  font-weight: 650;
}

.entry-guide__text {
  margin-top: 2px;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

@media (max-width: 767px) {
  .session-meta {
    width: 100%;
  }

  .session-meta__progress,
  .session-meta__timer {
    flex: 1 1 auto;
    justify-content: center;
  }

  .practice-shell {
    max-width: none;
  }

  .entry-guide__item {
    padding: var(--space-4);
  }
}
</style>
