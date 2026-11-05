<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { QuestionListItem } from '../../api/types'
import MarkdownRenderer from '../common/MarkdownRenderer.vue'
import {
  formatDate,
  masteryStatusColor,
  masteryStatusLabel,
  questionTypeLabel,
} from '../../utils/question'

const props = defineProps<{ question: QuestionListItem }>()

const detailPath = computed(() => `/questions/${props.question.id}`)
const createdAt = computed(() => formatDate(props.question.created_at))
const ariaLabel = computed(() => `查看错题 ${props.question.id}：${props.question.excerpt}`)
</script>

<template>
  <RouterLink :to="detailPath" class="question-card" :aria-label="ariaLabel">
    <a-card class="question-card__surface" :bordered="false">
      <div class="question-card__top">
        <div class="question-card__identity">
          <span class="question-card__id">#{{ question.id }}</span>
          <p class="question-card__subject">
            {{ question.subject }}
            <span v-if="question.chapter" class="question-card__chapter">
              · {{ question.chapter }}
            </span>
          </p>
        </div>
        <div class="question-card__badges">
          <a-tag size="small" color="gray">{{ questionTypeLabel(question.question_type) }}</a-tag>
          <a-tag size="small" :color="masteryStatusColor(question.mastery_status)">
            {{ masteryStatusLabel(question.mastery_status) }}
          </a-tag>
        </div>
      </div>

      <MarkdownRenderer class="question-card__excerpt" :content="question.excerpt" />

      <div class="question-card__footer">
        <ul v-if="question.tags.length" class="question-card__tags">
          <li v-for="tag in question.tags" :key="tag.id">
            <a-tag size="small">{{ tag.name }}</a-tag>
          </li>
        </ul>
        <time class="question-card__date" :datetime="question.created_at">{{ createdAt }}</time>
      </div>
    </a-card>
  </RouterLink>
</template>

<style scoped>
.question-card {
  display: block;
  border-radius: var(--radius-lg);
  color: inherit;
}

.question-card:hover {
  color: inherit;
}

.question-card__surface {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  transition:
    border-color 0.18s ease,
    background-color 0.18s ease;
}

.question-card:hover .question-card__surface {
  border-color: var(--color-primary);
  background: var(--color-surface-hover);
}

.question-card:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.question-card__surface :deep(.arco-card-body) {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5);
}

.question-card__top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.question-card__identity {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-2);
  min-width: 0;
}

.question-card__id {
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
  font-variant-numeric: tabular-nums;
}

.question-card__subject {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  font-weight: 500;
  line-height: var(--text-sm-leading);
}

.question-card__chapter {
  color: var(--color-text-3);
  font-weight: 400;
}

.question-card__badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.question-card__excerpt {
  color: var(--color-text-1);
  font-size: var(--text-base);
  line-height: var(--text-base-leading);
}

.question-card__excerpt :deep(p) {
  display: -webkit-box;
  overflow: hidden;
  text-wrap: pretty;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.question-card__excerpt :deep(a) {
  pointer-events: none;
}

.question-card__footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.question-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.question-card__date {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
}

@media (max-width: 767px) {
  .question-card__surface :deep(.arco-card-body) {
    padding: var(--space-4);
  }

  .question-card__footer {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
