<script setup lang="ts">
import { computed } from 'vue'
import type { GeneratedQuestion } from '../../api/types'
import MarkdownRenderer from '../common/MarkdownRenderer.vue'
import {
  difficultyColor,
  difficultyLabel,
  questionTypeLabel,
  validationStatusLabel,
} from '../../utils/question'

const props = defineProps<{
  question: GeneratedQuestion
  index: number
}>()

const typeLabel = computed(() => questionTypeLabel(props.question.question_type))
const difficultyTone = computed(() => difficultyColor(props.question.difficulty))
const difficultyText = computed(() => difficultyLabel(props.question.difficulty))
const hasOptions = computed(() => Boolean(props.question.options?.length))
const needsAttention = computed(() => props.question.validation_status !== 'valid')
</script>

<template>
  <a-card class="generated-question" :bordered="false">
    <header class="generated-question__header">
      <h3 class="generated-question__title">第 {{ index }} 题</h3>
      <div class="generated-question__badges">
        <a-tag v-if="question.question_type" size="small" color="gray">{{ typeLabel }}</a-tag>
        <a-tag size="small" :color="difficultyTone">{{ difficultyText }}</a-tag>
        <a-tag v-if="needsAttention" size="small" color="orange">
          {{ validationStatusLabel(question.validation_status) }}
        </a-tag>
      </div>
    </header>

    <MarkdownRenderer :content="question.content_md" />

    <ol v-if="hasOptions" class="generated-question__options">
      <li v-for="option in question.options" :key="option.label" class="generated-question__option">
        <span class="generated-question__option-label">{{ option.label }}</span>
        <MarkdownRenderer :content="option.content_md" compact />
      </li>
    </ol>

    <a-collapse class="generated-question__collapse" :bordered="false">
      <a-collapse-item key="answer" header="答案">
        <MarkdownRenderer :content="question.answer_md" compact />
      </a-collapse-item>
      <a-collapse-item key="explanation" header="解析">
        <MarkdownRenderer :content="question.explanation_md" compact />
      </a-collapse-item>
    </a-collapse>
  </a-card>
</template>

<style scoped>
.generated-question {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.generated-question :deep(.arco-card-body) {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-5);
}

.generated-question__header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.generated-question__title {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 500;
  line-height: var(--text-xs-leading);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.generated-question__badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.generated-question__options {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.generated-question__option {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.generated-question__option-label {
  min-width: 1.5em;
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 600;
  line-height: var(--text-sm-leading);
}

.generated-question__collapse {
  border-top: 1px solid var(--color-border);
}

.generated-question__collapse :deep(.arco-collapse-item) {
  border-bottom: 0;
}

.generated-question__collapse :deep(.arco-collapse-item-header) {
  padding-right: 0;
  padding-left: 0;
  border-bottom: 0;
  background: transparent;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  font-weight: 500;
}

.generated-question__collapse :deep(.arco-collapse-item-content) {
  background: transparent;
}

.generated-question__collapse :deep(.arco-collapse-item-content-box) {
  padding: var(--space-2) 0 0;
}

@media (max-width: 767px) {
  .generated-question :deep(.arco-card-body) {
    padding: var(--space-4);
  }
}
</style>
