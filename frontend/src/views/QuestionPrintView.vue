<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import LoadingSkeleton from '../components/common/LoadingSkeleton.vue'
import MarkdownRenderer from '../components/common/MarkdownRenderer.vue'
import { getQuestion, listQuestions } from '../api/questions'
import { normalizeApiError } from '../api/errors'
import type {
  GeneratedQuestion,
  MasteryStatus,
  QuestionBlank,
  QuestionDetail,
  QuestionListItem,
} from '../api/types'
import { masteryStatusLabel, questionTypeLabel } from '../utils/question'
import {
  buildPrintQuery,
  PRINT_CONCURRENCY,
  PRINT_LIMIT,
  PRINT_PAGE_SIZE,
  settleWithConcurrency,
} from '../utils/printWorksheet'

interface PrintEntry {
  item: QuestionListItem
  detail: QuestionDetail | null
  failure: string
}

interface AnswerBlock {
  key: string
  label: string
  answer: string
  explanation: string
  blanks: QuestionBlank[]
}

const MASTERY_VALUES: MasteryStatus[] = ['unmastered', 'reviewing', 'mastered']

const route = useRoute()
const router = useRouter()

const entries = ref<PrintEntry[]>([])
const loading = ref(true)
const errorMessage = ref('')
const errorCode = ref('')
const includeOriginal = ref(true)
const includeGenerated = ref(true)
const answersAtEnd = ref(true)

let requestToken = 0

const filterState = computed(() => ({
  q: readQueryValue(route.query.q).trim(),
  subject: readQueryValue(route.query.subject).trim(),
  tag: readQueryValue(route.query.tag).trim(),
  mastery_status: readQueryValue(route.query.mastery_status).trim(),
}))

const backQuery = computed(() =>
  buildPrintQuery({
    q: filterState.value.q,
    subject: filterState.value.subject,
    tag: filterState.value.tag,
    mastery_status: filterState.value.mastery_status,
  }),
)

const hasActiveFilters = computed(
  () =>
    Boolean(filterState.value.q) ||
    Boolean(filterState.value.subject) ||
    Boolean(filterState.value.tag) ||
    Boolean(filterState.value.mastery_status),
)

const filterChips = computed<string[]>(() => {
  const chips: string[] = []
  const state = filterState.value

  if (state.subject) chips.push(state.subject)
  if (state.mastery_status && isMasteryStatus(state.mastery_status)) {
    chips.push(masteryStatusLabel(state.mastery_status))
  }
  if (state.tag) chips.push(`#${state.tag}`)
  if (state.q) chips.push(`“${state.q}”`)

  return chips
})

const contentSummary = computed(() => {
  const parts: string[] = []
  if (includeOriginal.value) parts.push('原题')
  if (includeGenerated.value) parts.push('相似题')
  return parts.length ? `含${parts.join(' · ')}` : '未选择内容'
})

const failedNumbers = computed(() =>
  entries.value.flatMap((entry, index) => (entry.failure ? [index + 1] : [])),
)

const answerIndex = computed(() =>
  entries.value.map((entry, index) => ({
    number: index + 1,
    blocks: visibleAnswerBlocks(entry),
  })),
)

const printedAt = computed(() =>
  new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date()),
)

function readQueryValue(value: unknown): string {
  if (Array.isArray(value)) {
    const first = value[0]
    return typeof first === 'string' ? first : ''
  }
  return typeof value === 'string' ? value : ''
}

function isMasteryStatus(value: string): value is MasteryStatus {
  return (MASTERY_VALUES as string[]).includes(value)
}

function describeFailure(reason: unknown): string {
  try {
    return normalizeApiError(reason).message
  } catch {
    return '详情加载失败'
  }
}

async function loadWorksheet(): Promise<void> {
  const token = ++requestToken
  loading.value = true
  errorMessage.value = ''
  errorCode.value = ''
  entries.value = []

  try {
    const filters = filterState.value
    const result = await listQuestions({
      page: 1,
      page_size: PRINT_PAGE_SIZE,
      q: filters.q || undefined,
      subject: filters.subject || undefined,
      tag: filters.tag || undefined,
      mastery_status: isMasteryStatus(filters.mastery_status)
        ? filters.mastery_status
        : undefined,
      sort: 'created_at_desc',
    })

    if (token !== requestToken) return

    const selected = result.items.slice(0, PRINT_LIMIT)
    const settled = await settleWithConcurrency(selected, PRINT_CONCURRENCY, (item) =>
      getQuestion(item.id, { includeGenerated: true }),
    )

    if (token !== requestToken) return

    entries.value = selected.map((item, index) => {
      const outcome = settled[index]
      if (outcome?.status === 'fulfilled') {
        return { item, detail: outcome.value, failure: '' }
      }
      return {
        item,
        detail: null,
        failure: outcome ? describeFailure(outcome.reason) : '详情未加载',
      }
    })
  } catch (cause) {
    if (token !== requestToken) return
    const apiError = normalizeApiError(cause)
    errorMessage.value = apiError.message
    errorCode.value = apiError.code
  } finally {
    if (token === requestToken) loading.value = false
  }
}

function makeAnswerBlock(
  key: string,
  label: string,
  answer: string | null | undefined,
  explanation: string | null | undefined,
  blanks: QuestionBlank[] | null | undefined,
): AnswerBlock {
  return {
    key,
    label,
    answer: answer?.trim() ?? '',
    explanation: explanation?.trim() ?? '',
    blanks: blanks ?? [],
  }
}

function originalAnswerBlocks(entry: PrintEntry): AnswerBlock[] {
  if (!entry.detail) return []
  return [
    makeAnswerBlock(
      `q-${entry.detail.id}`,
      '原题',
      entry.detail.answer_md,
      entry.detail.explanation_md,
      entry.detail.blanks,
    ),
  ]
}

function generatedAnswerBlock(
  entry: PrintEntry,
  generated: GeneratedQuestion,
  index: number,
): AnswerBlock {
  return makeAnswerBlock(
    `g-${entry.item.id}-${generated.id}`,
    `相似题 ${index + 1}`,
    generated.answer_md,
    generated.explanation_md,
    generated.blanks,
  )
}

function visibleAnswerBlocks(entry: PrintEntry): AnswerBlock[] {
  const blocks: AnswerBlock[] = []

  if (includeOriginal.value) blocks.push(...originalAnswerBlocks(entry))
  if (includeGenerated.value && entry.detail) {
    entry.detail.generated_questions.forEach((generated, index) => {
      blocks.push(generatedAnswerBlock(entry, generated, index))
    })
  }

  return blocks
}

function hasAnswerContent(block: AnswerBlock): boolean {
  return Boolean(block.answer) || block.blanks.length > 0 || Boolean(block.explanation)
}

function handlePrint(): void {
  window.print()
}

function goBack(): void {
  void router.push({ name: 'questions', query: backQuery.value })
}

onMounted(() => {
  void loadWorksheet()
})
</script>

<template>
  <div class="print-page">
    <div class="config no-print" role="group" aria-label="打印设置">
      <RouterLink class="config__back" :to="{ name: 'questions', query: backQuery }">
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
          <path d="m15 6-6 6 6 6" />
        </svg>
        返回错题本
      </RouterLink>

      <div class="config__options">
        <label class="config__check">
          <input v-model="includeOriginal" type="checkbox" />
          包含原题
        </label>
        <label class="config__check">
          <input v-model="includeGenerated" type="checkbox" />
          包含相似题
        </label>
        <label class="config__check">
          <input v-model="answersAtEnd" type="checkbox" />
          答案统一附卷尾
        </label>
      </div>

      <button
        class="btn btn--primary"
        type="button"
        :disabled="!entries.length || (!includeOriginal && !includeGenerated)"
        @click="handlePrint"
      >
        <svg
          class="icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.7"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M6 9V3h12v6" />
          <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
          <path d="M6 14h12v7H6z" />
        </svg>
        打印 / 导出 PDF
      </button>
    </div>

    <LoadingSkeleton v-if="loading" variant="detail" label="正在整理巩固卷" />

    <ErrorState
      v-else-if="errorMessage"
      title="巩固卷加载失败"
      :message="errorMessage"
      :code="errorCode"
      @retry="loadWorksheet"
    />

    <EmptyState
      v-else-if="entries.length === 0"
      :title="hasActiveFilters ? '当前筛选没有错题' : '还没有错题'"
      :description="
        hasActiveFilters
          ? '换一个筛选条件，或返回错题本清空筛选后再导出。'
          : '录入错题后即可导出巩固卷。'
      "
      action-label="返回错题本"
      @action="goBack"
    />

    <template v-else>
      <p v-if="failedNumbers.length" class="print-warning no-print" role="status">
        第 {{ failedNumbers.join('、') }} 题详情加载失败，已用题干摘要占位；其余题目不受影响。
      </p>

      <article class="worksheet">
        <header class="worksheet__head">
          <p class="worksheet__brand">Bababoi 错题学习机</p>
          <h1>错题巩固卷</h1>
          <p class="worksheet__meta">
            <span v-if="filterChips.length">筛选：{{ filterChips.join(' · ') }}</span>
            <span>共 {{ entries.length }} 道</span>
            <span>{{ contentSummary }}</span>
            <span>{{ printedAt }}</span>
          </p>
          <p class="worksheet__hint no-print">
            使用浏览器打印（Ctrl/⌘ + P）可另存为 PDF；打印时配置栏会自动隐藏。
          </p>
        </header>

        <p v-if="!includeOriginal && !includeGenerated" class="worksheet__notice">
          请至少勾选「包含原题」或「包含相似题」后再打印。
        </p>

        <ol v-else class="question-list">
          <li
            v-for="(entry, index) in entries"
            :key="entry.item.id"
            class="question-block"
          >
            <header class="question-block__head">
              <span class="question-block__no" aria-hidden="true">{{ index + 1 }}</span>
              <span class="tag">{{ questionTypeLabel(entry.item.question_type) }}</span>
              <span class="tag tag--point">{{ entry.item.subject }}</span>
              <span v-if="entry.item.chapter" class="tag tag--point">
                {{ entry.item.chapter }}
              </span>
              <span
                v-for="tag in entry.item.tags"
                :key="tag.id"
                class="tag"
              >{{ tag.name }}</span>
            </header>

            <template v-if="includeOriginal">
              <div class="question-block__stem">
                <MarkdownRenderer
                  v-if="entry.detail"
                  :content="entry.detail.content_md"
                />
                <p v-else class="question-block__fallback">{{ entry.item.excerpt }}</p>
              </div>

              <ol v-if="entry.detail?.options?.length" class="question-options">
                <li
                  v-for="option in entry.detail?.options ?? []"
                  :key="option.label"
                  class="question-options__item"
                >
                  <span class="question-options__label">{{ option.label }}</span>
                  <MarkdownRenderer :content="option.content_md" compact />
                </li>
              </ol>

              <p v-if="answersAtEnd" class="answer-pointer">答案见卷尾。</p>

              <template v-if="!answersAtEnd">
                <div
                  v-for="block in originalAnswerBlocks(entry)"
                  :key="block.key"
                  class="answer-card"
                >
                  <div v-if="block.answer" class="answer-card__row">
                    <span class="inline-label">答案</span>
                    <MarkdownRenderer :content="block.answer" />
                  </div>
                  <div v-if="block.blanks.length" class="answer-card__row">
                    <span class="inline-label">填空答案</span>
                    <ul class="answer-card__blanks">
                      <li v-for="blank in block.blanks" :key="blank.index">
                        <span class="answer-card__blank-label">第 {{ blank.index }} 空</span>
                        <MarkdownRenderer :content="blank.answer_md" compact />
                      </li>
                    </ul>
                  </div>
                  <div v-if="block.explanation" class="answer-card__row">
                    <span class="inline-label">解析</span>
                    <MarkdownRenderer :content="block.explanation" />
                  </div>
                  <p v-if="!hasAnswerContent(block)" class="answer-card__empty">
                    暂无答案与解析。
                  </p>
                </div>
              </template>
            </template>

            <template v-if="includeGenerated">
              <div
                v-for="(generated, generatedIndex) in entry.detail?.generated_questions ?? []"
                :key="generated.id"
                class="generated-block"
              >
                <header class="generated-block__head">
                  <span class="generated-block__label">
                    相似题 {{ generatedIndex + 1 }}
                  </span>
                  <span class="tag">{{ questionTypeLabel(generated.question_type) }}</span>
                </header>

                <div class="generated-block__stem">
                  <MarkdownRenderer :content="generated.content_md" />
                </div>

                <ol v-if="generated.options?.length" class="question-options">
                  <li
                    v-for="option in generated.options"
                    :key="option.label"
                    class="question-options__item"
                  >
                    <span class="question-options__label">{{ option.label }}</span>
                    <MarkdownRenderer :content="option.content_md" compact />
                  </li>
                </ol>

                <p v-if="answersAtEnd" class="answer-pointer">答案见卷尾。</p>

                <div v-else class="answer-card">
                  <div v-if="generated.answer_md.trim()" class="answer-card__row">
                    <span class="inline-label">答案</span>
                    <MarkdownRenderer :content="generated.answer_md" />
                  </div>
                  <div v-if="generated.blanks?.length" class="answer-card__row">
                    <span class="inline-label">填空答案</span>
                    <ul class="answer-card__blanks">
                      <li v-for="blank in generated.blanks" :key="blank.index">
                        <span class="answer-card__blank-label">第 {{ blank.index }} 空</span>
                        <MarkdownRenderer :content="blank.answer_md" compact />
                      </li>
                    </ul>
                  </div>
                  <div v-if="generated.explanation_md.trim()" class="answer-card__row">
                    <span class="inline-label">解析</span>
                    <MarkdownRenderer :content="generated.explanation_md" />
                  </div>
                  <p
                    v-if="
                      !generated.answer_md.trim() &&
                      !generated.blanks?.length &&
                      !generated.explanation_md.trim()
                    "
                    class="answer-card__empty"
                  >
                    暂无答案与解析。
                  </p>
                </div>
              </div>

              <p
                v-if="entry.detail && !entry.detail.generated_questions.length"
                class="question-block__note"
              >
                这道题暂无相似题。
              </p>
              <p v-else-if="!entry.detail" class="question-block__note">
                相似题详情加载失败，仅显示原题摘要。
              </p>
            </template>
          </li>
        </ol>
      </article>

      <section v-if="answersAtEnd" class="answer-key" aria-labelledby="answer-key-title">
        <h2 id="answer-key-title">参考答案与解析</h2>

        <div
          v-for="entry in answerIndex"
          :key="entry.number"
          class="answer-key__item"
        >
          <h3>第 {{ entry.number }} 题</h3>

          <template v-if="entry.blocks.length">
            <div
              v-for="block in entry.blocks"
              :key="block.key"
              class="answer-card"
            >
              <header class="answer-card__head">
                <span class="answer-card__label">{{ block.label }}</span>
              </header>
              <div v-if="block.answer" class="answer-card__row">
                <span class="inline-label">答案</span>
                <MarkdownRenderer :content="block.answer" />
              </div>
              <div v-if="block.blanks.length" class="answer-card__row">
                <span class="inline-label">填空答案</span>
                <ul class="answer-card__blanks">
                  <li v-for="blank in block.blanks" :key="blank.index">
                    <span class="answer-card__blank-label">第 {{ blank.index }} 空</span>
                    <MarkdownRenderer :content="blank.answer_md" compact />
                  </li>
                </ul>
              </div>
              <div v-if="block.explanation" class="answer-card__row">
                <span class="inline-label">解析</span>
                <MarkdownRenderer :content="block.explanation" />
              </div>
              <p v-if="!hasAnswerContent(block)" class="answer-card__empty">
                暂无答案与解析。
              </p>
            </div>
          </template>

          <p v-else class="answer-card__empty">
            这道题暂无答案与解析。
          </p>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.print-page {
  display: block;
}

.config {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3) var(--space-5);
  margin-bottom: var(--space-5);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.config__back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 34px;
  color: var(--color-primary-active);
  font-size: var(--text-sm);
  font-weight: 600;
}

.config__back .icon {
  width: 16px;
  height: 16px;
}

.config__options {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
}

.config__check {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 34px;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  cursor: pointer;
}

.config__check input {
  width: 16px;
  height: 16px;
  accent-color: var(--color-primary);
}

.config .btn {
  margin-left: auto;
}

.print-warning {
  margin-bottom: var(--space-4);
  padding: 10px var(--space-4);
  border: 1px solid var(--color-warning-border);
  border-radius: var(--radius-md);
  background: var(--color-warning-soft);
  color: var(--color-warning-text);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.worksheet,
.answer-key {
  max-width: 780px;
  margin: 0 auto;
  padding: var(--space-7);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  color: var(--color-text-1);
}

.answer-key {
  margin-top: var(--space-6);
}

.worksheet__head {
  padding-bottom: var(--space-4);
  border-bottom: 2px solid var(--color-text-1);
}

.worksheet__brand {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 600;
  letter-spacing: 0.08em;
}

.worksheet h1 {
  margin-top: var(--space-2);
  font-size: var(--text-2xl);
  line-height: var(--text-2xl-leading);
  letter-spacing: -0.01em;
}

.worksheet__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-4);
  margin-top: var(--space-2);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.worksheet__hint {
  margin-top: var(--space-2);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.worksheet__notice {
  margin-top: var(--space-5);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
  color: var(--color-text-2);
  font-size: var(--text-sm);
}

.question-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  margin: var(--space-5) 0 0;
  padding: 0;
  list-style: none;
}

.question-block {
  min-width: 0;
}

.question-block__head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
}

.question-block__no {
  display: inline-grid;
  place-items: center;
  min-width: 28px;
  height: 28px;
  flex: none;
  padding: 0 6px;
  border-radius: var(--radius-sm);
  background: var(--color-primary-soft);
  color: var(--color-primary-active);
  font-size: var(--text-sm);
  font-weight: 650;
  line-height: 1;
}

.question-block__stem,
.generated-block__stem {
  margin-top: var(--space-2);
  font-weight: 500;
  text-wrap: pretty;
}

.question-block__fallback {
  color: var(--color-text-2);
}

.question-block__note {
  margin-top: var(--space-3);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.question-options {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin: var(--space-2) 0 0;
  padding: 0;
  list-style: none;
}

.question-options__item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  min-width: 0;
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

.generated-block {
  min-width: 0;
  margin-top: var(--space-4);
  padding-left: var(--space-4);
  border-left: 1px solid var(--color-border);
}

.generated-block:first-child {
  margin-top: var(--space-3);
}

.generated-block__head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
}

.generated-block__label {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  font-weight: 650;
}

.answer-pointer {
  margin-top: var(--space-2);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.answer-card {
  margin-top: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
}

.answer-card__head {
  margin-bottom: 6px;
}

.answer-card__label {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  font-weight: 650;
}

.answer-card__row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  min-width: 0;
}

.answer-card__row + .answer-card__row {
  margin-top: var(--space-2);
}

.answer-card__row .inline-label {
  flex: none;
  margin-right: 0;
  line-height: var(--text-base-leading);
}

.answer-card__row :deep(.markdown-renderer) {
  flex: 1;
  min-width: 0;
}

.answer-card__blanks {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}

.answer-card__blanks li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  min-width: 0;
}

.answer-card__blank-label {
  flex: none;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-base-leading);
}

.answer-card__empty {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.answer-key h2 {
  margin-bottom: var(--space-4);
  font-size: var(--text-xl);
  line-height: var(--text-xl-leading);
}

.answer-key__item + .answer-key__item {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.answer-key__item h3 {
  margin-bottom: var(--space-2);
  font-size: var(--text-base);
  line-height: 24px;
}

@media (max-width: 767px) {
  .config {
    gap: var(--space-2) var(--space-3);
    padding: var(--space-3);
  }

  .config .btn {
    width: 100%;
    margin-left: 0;
  }

  .worksheet,
  .answer-key {
    padding: var(--space-4);
    border-radius: var(--radius-md);
  }

  .worksheet h1 {
    font-size: var(--text-xl);
    line-height: var(--text-xl-leading);
  }

  .question-list {
    gap: var(--space-5);
  }

  .generated-block {
    padding-left: var(--space-3);
  }

  .answer-card {
    padding: var(--space-3);
  }
}

@media print {
  .no-print {
    display: none !important;
  }

  .worksheet,
  .answer-key {
    max-width: none;
    margin: 0;
    padding: 0;
    border: 0;
    border-radius: 0;
    background: transparent;
  }

  .answer-key {
    break-before: page;
    page-break-before: always;
    margin-top: 0;
  }

  .question-block,
  .generated-block,
  .answer-key__item {
    break-inside: avoid;
    page-break-inside: avoid;
  }

  .worksheet h1 {
    font-size: 20pt;
    line-height: 1.25;
  }

  .worksheet__meta,
  .question-block__note,
  .answer-pointer,
  .answer-card__label,
  .answer-card__blank-label {
    print-color-adjust: exact;
  }

  .answer-card {
    background: transparent;
  }

  .worksheet :deep(.markdown-renderer),
  .answer-key :deep(.markdown-renderer) {
    overflow-wrap: anywhere;
    font-size: 11pt;
    line-height: 1.55;
  }

  .worksheet :deep(.katex),
  .answer-key :deep(.katex) {
    font-size: 1em;
  }

  .worksheet :deep(.katex-display),
  .answer-key :deep(.katex-display) {
    margin: 0;
  }

  .worksheet :deep(.md-math-block),
  .worksheet :deep(.md-math-display),
  .worksheet :deep(pre),
  .answer-key :deep(.md-math-block),
  .answer-key :deep(.md-math-display),
  .answer-key :deep(pre) {
    overflow: visible;
  }

  .worksheet :deep(img),
  .worksheet :deep(.mermaid-block__canvas svg),
  .answer-key :deep(img),
  .answer-key :deep(.mermaid-block__canvas svg) {
    max-width: 100% !important;
    height: auto !important;
  }
}
</style>
