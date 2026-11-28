<script setup lang="ts">
import { computed } from 'vue'
import type { GeneratedQuestion } from '../../api/types'
import MarkdownRenderer from '../common/MarkdownRenderer.vue'
import { difficultyLabel, formatDate, questionTypeLabel } from '../../utils/question'

const props = defineProps<{
  question: GeneratedQuestion
  index: number
}>()

const number = computed(() => String(props.index).padStart(2, '0'))
const typeText = computed(() => questionTypeLabel(props.question.question_type))
const difficultyText = computed(() => difficultyLabel(props.question.difficulty))
const hasOptions = computed(() => Boolean(props.question.options?.length))
const blanks = computed(() => props.question.blanks ?? [])
const practiceText = computed(() => {
  if (props.question.practice_count === undefined) return ''
  const total = props.question.practice_count
  const correct = props.question.correct_count ?? 0
  const last = props.question.last_practiced_at
    ? ` · 最近 ${formatDate(props.question.last_practiced_at)}`
    : ''
  return `练习 ${total} 次 · 答对 ${correct} 次${last}`
})
const hasQa = computed(
  () =>
    Boolean(props.question.answer_md?.trim()) ||
    blanks.value.length > 0 ||
    Boolean(props.question.explanation_md?.trim()),
)
</script>

<template>
  <article class="gen-card">
    <div class="gen-card__head">
      <span class="gen-card__no" aria-hidden="true">{{ number }}</span>
      <div class="gen-card__tags">
        <span class="tag">{{ typeText }}</span>
        <span class="tag tag--point">{{ difficultyText }}</span>
      </div>
    </div>

    <div class="gen-card__stem">
      <MarkdownRenderer :content="question.content_md" />
    </div>

    <ol v-if="hasOptions" class="gen-card__options">
      <li v-for="option in question.options" :key="option.label" class="gen-card__option">
        <span class="gen-card__option-label">{{ option.label }}</span>
        <MarkdownRenderer :content="option.content_md" compact />
      </li>
    </ol>

    <p v-if="practiceText" class="gen-card__practice">{{ practiceText }}</p>

    <details class="collapse collapse--card">
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
        答案与解析
        <span class="collapse__state" aria-hidden="true" />
      </summary>
      <div class="collapse__body">
        <template v-if="hasQa">
          <div v-if="question.answer_md?.trim()" class="gen-qa">
            <span class="inline-label">答案</span>
            <MarkdownRenderer :content="question.answer_md" />
          </div>
          <div v-if="blanks.length" class="gen-qa">
            <span class="inline-label">填空答案</span>
            <ul class="gen-blanks">
              <li v-for="blank in blanks" :key="blank.index" class="gen-blanks__item">
                <span class="gen-blanks__label">第 {{ blank.index }} 空</span>
                <MarkdownRenderer :content="blank.answer_md" compact />
              </li>
            </ul>
          </div>
          <div v-if="question.explanation_md?.trim()" class="gen-qa">
            <span class="inline-label">解析</span>
            <MarkdownRenderer :content="question.explanation_md" />
          </div>
        </template>
        <p v-else class="gen-qa-empty">暂无答案与解析。</p>
      </div>
    </details>

  </article>
</template>

<style scoped>
.gen-card {
  min-width: 0;
  padding: 15px var(--space-5) 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.gen-card__head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.gen-card__no {
  color: var(--color-primary-active);
  font-family: var(--font-math);
  font-size: 22px;
  font-weight: 400;
  line-height: 1;
}

.gen-card__tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px;
  margin-left: auto;
}

.gen-card__stem {
  max-width: 50em;
  margin-top: 7px;
  font-size: var(--text-base);
  line-height: var(--text-base-leading);
  font-weight: 500;
  text-wrap: pretty;
}

.gen-card__stem :deep(.markdown-renderer) {
  font-weight: 500;
}

.gen-card__stem :deep(.markdown-renderer p) {
  margin-bottom: var(--space-2);
}

.gen-card__stem :deep(.markdown-renderer > :last-child) {
  margin-bottom: 0;
}

.gen-card__options {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: var(--space-3) 0 0;
  padding: 0;
  list-style: none;
}

.gen-card__practice {
  margin-top: var(--space-2);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-variant-numeric: tabular-nums;
}

.gen-card__option {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.gen-card__option-label {
  flex: none;
  min-width: 1.5em;
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 600;
  line-height: var(--text-sm-leading);
}

.collapse--card {
  margin-top: 8px;
  border-top: 1px solid var(--color-border);
}

.gen-card .collapse__body {
  padding-bottom: var(--space-4);
}

.gen-qa {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  min-width: 0;
}

.gen-qa + .gen-qa {
  margin-top: var(--space-2);
}

.gen-qa .inline-label {
  flex: none;
  margin-right: 0;
  line-height: var(--text-base-leading);
}

.gen-qa :deep(.markdown-renderer) {
  flex: 1;
  min-width: 0;
  font-size: var(--text-base);
  line-height: var(--text-base-leading);
}

.gen-qa :deep(.markdown-renderer p) {
  margin-bottom: var(--space-1);
}

.gen-qa :deep(.markdown-renderer > :last-child) {
  margin-bottom: 0;
}

.gen-blanks {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}

.gen-blanks__item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  min-width: 0;
}

.gen-blanks__label {
  flex: none;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-base-leading);
}

.gen-qa-empty {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

@media (max-width: 767px) {
  .gen-card {
    padding: 14px var(--space-4) 8px;
  }
}
</style>
