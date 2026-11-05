<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { MasteryStatus, QuestionListItem } from '../../api/types'
import MarkdownRenderer from '../common/MarkdownRenderer.vue'
import { masteryStatusLabel, questionTypeLabel } from '../../utils/question'

const props = defineProps<{ question: QuestionListItem }>()

const MASTERY_TAG_CLASSES: Record<MasteryStatus, string> = {
  unmastered: 'tag--unmastered',
  reviewing: 'tag--reviewing',
  mastered: 'tag--mastered',
}

const detailPath = computed(() => `/questions/${props.question.id}`)
const createdAt = computed(() => formatCardDate(props.question.created_at))
const ariaLabel = computed(() => `查看错题 ${props.question.id}：${props.question.excerpt}`)
const masteryTagClass = computed(() => MASTERY_TAG_CLASSES[props.question.mastery_status])

function formatCardDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  const pad = (part: number): string => String(part).padStart(2, '0')
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}
</script>

<template>
  <RouterLink :to="detailPath" class="question-card" :aria-label="ariaLabel">
    <article class="qcard">
      <div class="qcard__head">
        <span class="qcard__id">#{{ question.id }}</span>
        <p class="qcard__subject">
          {{ question.subject
          }}<span v-if="question.chapter" class="qcard__chapter">
            <span class="sep">·</span>{{ question.chapter }}</span
          >
        </p>
        <div class="qcard__badges">
          <span class="tag qcard__type">{{ questionTypeLabel(question.question_type) }}</span>
          <span class="tag" :class="masteryTagClass">
            <span class="dot" aria-hidden="true"></span>
            {{ masteryStatusLabel(question.mastery_status) }}
          </span>
        </div>
      </div>

      <div class="qcard__stem">
        <MarkdownRenderer :content="question.excerpt" />
      </div>

      <div class="qcard__foot">
        <ul v-if="question.tags.length" class="qcard__tags" aria-label="知识点">
          <li v-for="tag in question.tags" :key="tag.id">
            <span class="tag tag--point">{{ tag.name }}</span>
          </li>
        </ul>
        <p class="qcard__facts">
          <span>{{ questionTypeLabel(question.question_type) }}</span>
          <span class="fact-dot" aria-hidden="true"></span>
          <time :datetime="question.created_at">{{ createdAt }}</time>
        </p>
      </div>
    </article>
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

.question-card:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 3px;
}

.qcard {
  padding: 17px var(--space-5) 15px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease;
}

.question-card:hover .qcard {
  border-color: var(--color-border-strong);
  background: var(--color-surface-hover);
}

.qcard__head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.qcard__id {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  letter-spacing: 0.02em;
}

.qcard__subject {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 500;
}

.qcard__subject .sep {
  margin: 0 4px;
  color: var(--color-border-strong);
}

.qcard__badges {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-left: auto;
}

.qcard__stem {
  max-width: 54em;
  margin-top: 8px;
  color: var(--color-text-1);
  font-size: var(--text-base);
  line-height: var(--text-base-leading);
  font-weight: 500;
  text-wrap: pretty;
}

.qcard__stem :deep(.markdown-renderer) {
  color: inherit;
  font-size: inherit;
  line-height: inherit;
}

.qcard__stem :deep(p) {
  display: -webkit-box;
  overflow: hidden;
  text-wrap: pretty;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.qcard__stem :deep(a) {
  color: inherit;
  text-decoration: none;
  pointer-events: none;
}

.qcard__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px var(--space-3);
  margin-top: 12px;
  padding-top: 11px;
  border-top: 1px solid var(--color-border);
}

.qcard__tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.qcard__facts {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  margin-left: auto;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.fact-dot {
  width: 2px;
  height: 2px;
  border-radius: 50%;
  background: var(--color-border-strong);
}

.qcard__facts time {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

@media (max-width: 767px) {
  .qcard {
    padding: 14px var(--space-4) 12px;
  }

  .qcard__stem {
    margin-top: 6px;
  }

  .qcard__foot {
    align-items: flex-start;
    flex-direction: column;
  }

  .qcard__facts {
    width: 100%;
    justify-content: space-between;
    margin-left: 0;
  }
}

@media (max-width: 480px) {
  .qcard__type {
    display: none;
  }
}
</style>
