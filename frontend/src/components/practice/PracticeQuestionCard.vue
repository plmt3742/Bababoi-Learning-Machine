<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { GeneratedQuestion } from '../../api/types'
import { difficultyLabel, questionTypeLabel } from '../../utils/question'
import {
  blankAnswerCount,
  buildPracticeUserAnswer,
  resolvePracticeQuestionType,
} from '../../utils/practice'
import MarkdownRenderer from '../common/MarkdownRenderer.vue'

const props = defineProps<{
  question: GeneratedQuestion
  index: number
  total: number
  submitting: boolean
  submitError: string
}>()

const emit = defineEmits<{
  grade: [isCorrect: boolean, userAnswer: string | null]
  retry: []
}>()

const choiceAnswer = ref('')
const blankAnswers = ref<string[]>(
  Array.from({ length: blankAnswerCount(props.question) }, () => ''),
)
const solveAnswer = ref('')
const revealed = ref(false)

const effectiveType = computed(() => resolvePracticeQuestionType(props.question))
const typeLabel = computed(() => questionTypeLabel(effectiveType.value))
const difficultyText = computed(() =>
  props.question.difficulty ? difficultyLabel(props.question.difficulty) : '',
)
const questionNumber = computed(() => props.index + 1)
const choiceOptions = computed(() =>
  effectiveType.value === 'choice' ? (props.question.options ?? []) : [],
)
const blanks = computed(() => props.question.blanks ?? [])
const blankFields = computed(() =>
  Array.from({ length: blankAnswerCount(props.question) }, (_, index) => index),
)
const answerText = computed(() => props.question.answer_md?.trim() ?? '')
const explanationText = computed(() => props.question.explanation_md?.trim() ?? '')
const hasAnswerContent = computed(() => Boolean(answerText.value) || blanks.value.length > 0)

function resetAnswer(): void {
  choiceAnswer.value = ''
  blankAnswers.value = Array.from({ length: blankAnswerCount(props.question) }, () => '')
  solveAnswer.value = ''
  revealed.value = false
}

function toggleReveal(): void {
  revealed.value = !revealed.value
}

function grade(isCorrect: boolean): void {
  if (props.submitting) return

  emit(
    'grade',
    isCorrect,
    buildPracticeUserAnswer(effectiveType.value, {
      choice: choiceAnswer.value,
      blanks: blankAnswers.value,
      solve: solveAnswer.value,
    }),
  )
}

watch(() => props.question.id, resetAnswer)
</script>

<template>
  <div class="practice-question">
    <article class="paper practice-card" aria-labelledby="practice-question-title">
      <div class="practice-card__head">
        <div class="practice-card__tags">
          <span class="tag">{{ typeLabel }}</span>
          <span v-if="difficultyText" class="tag tag--point">{{ difficultyText }}</span>
        </div>
        <span class="practice-card__id">#{{ question.id }}</span>
      </div>

      <div class="practice-card__body">
        <h2 id="practice-question-title" class="sr-only">第 {{ questionNumber }} 题</h2>
        <div class="practice-stem">
          <MarkdownRenderer :content="question.content_md" />
        </div>

        <div class="answer-area">
          <p class="answer-area__label">你的作答</p>

          <div
            v-if="effectiveType === 'choice' && choiceOptions.length > 0"
            class="option-list"
            role="radiogroup"
            aria-label="选择一个答案"
          >
            <label
              v-for="option in choiceOptions"
              :key="option.label"
              class="option"
              :class="{ 'option--selected': choiceAnswer === option.label }"
            >
              <input
                v-model="choiceAnswer"
                class="sr-only"
                type="radio"
                name="practice-choice"
                :value="option.label"
              />
              <span class="option__key" aria-hidden="true">{{ option.label }}</span>
              <div class="option__content">
                <MarkdownRenderer :content="option.content_md" compact />
              </div>
            </label>
          </div>

          <div v-else-if="effectiveType === 'blank'" class="blank-list">
            <label v-for="fieldIndex in blankFields" :key="fieldIndex" class="blank-field">
              <span class="blank-field__label">第 {{ fieldIndex + 1 }} 空</span>
              <input
                v-model="blankAnswers[fieldIndex]"
                class="input"
                type="text"
                :placeholder="`填写第 ${fieldIndex + 1} 空的答案`"
                autocomplete="off"
              />
            </label>
          </div>

          <label v-else class="solution-field">
            <span class="sr-only">解答过程</span>
            <textarea
              v-model="solveAnswer"
              class="textarea solution-field__input"
              rows="6"
              placeholder="写下你的解答过程或关键步骤…"
            />
          </label>
        </div>
      </div>

      <div class="practice-card__foot">
        <button
          class="btn btn--outline reveal-btn"
          type="button"
          :aria-expanded="revealed"
          @click="toggleReveal"
        >
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
            <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" />
            <circle cx="12" cy="12" r="2.6" />
          </svg>
          {{ revealed ? '收起答案' : '查看答案' }}
        </button>

        <div class="grade-group">
          <p class="grade-hint">
            {{ revealed ? '对照答案，诚实自评' : '完成后自评，提交即记录' }}
          </p>
          <div class="grade-actions">
            <button
              class="btn btn--outline grade-btn"
              type="button"
              :disabled="submitting"
              @click="grade(false)"
            >
              不会
            </button>
            <button
              class="btn btn--primary grade-btn"
              type="button"
              :disabled="submitting"
              @click="grade(true)"
            >
              会
            </button>
          </div>
        </div>
      </div>

      <div v-if="submitting" class="practice-card__status" role="status">正在保存练习记录…</div>

      <div v-if="submitError" class="submit-error" role="alert">
        <span>提交失败：{{ submitError }}</span>
        <button
          class="btn btn--quiet btn--sm"
          type="button"
          :disabled="submitting"
          @click="emit('retry')"
        >
          重试
        </button>
      </div>
    </article>

    <Transition name="answer-reveal">
      <section v-if="revealed" class="paper answer-panel" aria-live="polite">
        <div class="paper__head">
          <h2>参考答案</h2>
          <span class="paper__meta">{{ typeLabel }}</span>
        </div>
        <div class="paper__body">
          <div v-if="hasAnswerContent" class="answer-block">
            <p class="answer-block__label">答案</p>
            <MarkdownRenderer v-if="answerText" :content="answerText" />
            <ul v-if="blanks.length" class="blank-answers">
              <li v-for="blank in blanks" :key="blank.index" class="blank-answers__item">
                <span class="blank-answers__label">第 {{ blank.index }} 空</span>
                <MarkdownRenderer :content="blank.answer_md" compact />
              </li>
            </ul>
          </div>

          <div v-if="explanationText" class="answer-block">
            <p class="answer-block__label">解析</p>
            <MarkdownRenderer :content="explanationText" />
          </div>

          <p v-if="!hasAnswerContent && !explanationText" class="answer-empty">
            暂无答案与解析，可以直接自评。
          </p>
        </div>
      </section>
    </Transition>
  </div>
</template>

<style scoped>
.practice-question {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-width: 0;
}

.practice-card {
  overflow: hidden;
  min-width: 0;
}

.practice-card__head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-2);
  padding: 12px var(--space-6);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface-subtle);
}

.practice-card__tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.practice-card__id {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.practice-card__body {
  padding: var(--space-5) var(--space-6) var(--space-6);
}

.practice-stem {
  max-width: 50em;
  color: var(--color-text-1);
  font-size: var(--text-base);
  line-height: var(--text-base-leading);
  font-weight: 500;
  text-wrap: pretty;
}

.practice-stem :deep(.markdown-renderer) {
  font-weight: 500;
}

.practice-stem :deep(.markdown-renderer p) {
  margin-bottom: var(--space-2);
}

.practice-stem :deep(.markdown-renderer > :last-child) {
  margin-bottom: 0;
}

.answer-area {
  margin-top: var(--space-6);
  padding-top: var(--space-4);
  border-top: 1px dashed var(--color-border);
}

.answer-area__label {
  margin-bottom: var(--space-2);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 600;
  letter-spacing: 0.04em;
}

.option-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
  padding: 10px var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.option:hover {
  border-color: var(--color-border-strong);
  background: var(--color-surface-hover);
}

.option:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.option--selected {
  border-color: var(--color-primary);
  background: var(--color-primary-softer);
}

.option__key {
  display: grid;
  place-items: center;
  flex: none;
  width: 26px;
  height: 26px;
  border: 1px solid var(--color-border-strong);
  border-radius: 50%;
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 600;
  line-height: 1;
}

.option--selected .option__key {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-on-primary);
}

.option__content {
  flex: 1;
  min-width: 0;
  padding-top: 2px;
}

.option__content :deep(.markdown-renderer) {
  font-size: 15px;
  line-height: 24px;
}

.option__content :deep(.markdown-renderer p) {
  margin-bottom: 0;
}

.blank-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.blank-field {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-3);
}

.blank-field__label {
  flex: none;
  min-width: 4.5em;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.blank-field .input {
  flex: 1 1 180px;
  min-width: 0;
}

.solution-field {
  display: block;
}

.solution-field__input {
  min-height: 148px;
}

.practice-card__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-6);
  border-top: 1px solid var(--color-border);
  background: var(--color-surface-subtle);
}

.reveal-btn {
  background: var(--color-surface);
}

.grade-group {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-left: auto;
}

.grade-hint {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.grade-actions {
  display: flex;
  gap: var(--space-2);
}

.grade-btn {
  min-width: 74px;
}

.practice-card__status {
  padding: 10px var(--space-6);
  border-top: 1px solid var(--color-border);
  background: var(--color-primary-softer);
  color: var(--color-primary-active);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.submit-error {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-2);
  padding: 10px var(--space-6);
  border-top: 1px solid var(--color-danger-border);
  background: var(--color-danger-soft);
  color: var(--color-danger-text);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.answer-panel {
  overflow: hidden;
  min-width: 0;
}

.answer-panel .paper__head {
  background: var(--color-surface-subtle);
}

.answer-block + .answer-block {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.answer-block__label {
  margin-bottom: var(--space-2);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 600;
  letter-spacing: 0.04em;
}

.blank-answers {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: var(--space-2) 0 0;
  padding: 0;
  list-style: none;
}

.blank-answers__item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  min-width: 0;
}

.blank-answers__label {
  flex: none;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-base-leading);
}

.answer-empty {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.answer-reveal-enter-active,
.answer-reveal-leave-active {
  transition:
    opacity 0.16s ease,
    transform 0.16s ease;
}

.answer-reveal-enter-from,
.answer-reveal-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (max-width: 767px) {
  .practice-card__head {
    padding: 12px var(--space-4);
  }

  .practice-card__body {
    padding: var(--space-4);
  }

  .answer-area {
    margin-top: var(--space-5);
    padding-top: var(--space-3);
  }

  .practice-card__foot {
    align-items: stretch;
    flex-direction: column;
    padding: var(--space-3) var(--space-4);
  }

  .reveal-btn {
    width: 100%;
  }

  .grade-group {
    align-items: stretch;
    flex-direction: column;
    margin-left: 0;
    gap: var(--space-2);
  }

  .grade-hint {
    text-align: center;
  }

  .grade-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .grade-btn {
    width: 100%;
    min-height: 42px;
  }

  .practice-card__status,
  .submit-error {
    padding: 10px var(--space-4);
  }
}
</style>
