<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { MasteryStatus, QuestionListItem } from '../../api/types'
import MarkdownRenderer from '../common/MarkdownRenderer.vue'
import HomeSectionNotice from './HomeSectionNotice.vue'
import { masteryStatusLabel } from '../../utils/question'
import { formatStatsTime } from '../../utils/stats'

withDefaults(
  defineProps<{
    questions: QuestionListItem[]
    errorText?: string
  }>(),
  { errorText: '' },
)

const emit = defineEmits<{ retry: [] }>()

const MASTERY_TAG_CLASSES: Record<MasteryStatus, string> = {
  unmastered: 'tag--unmastered',
  reviewing: 'tag--reviewing',
  mastered: 'tag--mastered',
}
</script>

<template>
  <section class="panel" aria-labelledby="home-recent-title">
    <header class="panel__head">
      <h2 id="home-recent-title">最近错题</h2>
      <RouterLink class="panel__head-link" to="/questions">
        查看全部
        <svg
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
      </RouterLink>
    </header>

    <HomeSectionNotice
      v-if="errorText"
      tone="error"
      :title="questions.length > 0 ? '最近错题刷新失败' : '最近错题加载失败'"
      :message="errorText"
      action-label="重试"
      @action="emit('retry')"
    />

    <HomeSectionNotice
      v-else-if="questions.length === 0"
      title="还没有错题"
      message="录入第一道错题后，AI 会分析考点并生成 3 道相似题。"
      action-label="录入错题"
      action-to="/questions/new"
    />

    <ul v-if="questions.length > 0" class="recent">
      <li v-for="question in questions" :key="question.id" class="recent__item">
        <RouterLink
          class="recent__link"
          :to="`/questions/${question.id}`"
          :aria-label="`查看错题 ${question.id}：${question.excerpt}`"
        >
          <div class="recent__top">
            <p class="recent__subject">
              {{ question.subject
              }}<span v-if="question.chapter" class="recent__chapter">
                <span class="recent__sep" aria-hidden="true">·</span>
                {{ question.chapter }}</span
              >
            </p>
            <span class="tag" :class="MASTERY_TAG_CLASSES[question.mastery_status]">
              <span class="dot" aria-hidden="true" />
              {{ masteryStatusLabel(question.mastery_status) }}
            </span>
          </div>

          <div class="recent__excerpt">
            <MarkdownRenderer :content="question.excerpt" compact />
          </div>

          <div class="recent__bottom">
            <ul v-if="question.tags.length" class="recent__tags" aria-label="知识点">
              <li v-for="tag in question.tags" :key="tag.id">
                <span class="tag tag--point">{{ tag.name }}</span>
              </li>
            </ul>
            <time class="recent__time" :datetime="question.created_at">
              {{ formatStatsTime(question.created_at) }}
            </time>
          </div>
        </RouterLink>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.panel__head-link {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-left: auto;
  color: var(--color-primary-active);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 500;
}

.panel__head-link:hover {
  color: var(--color-primary);
}

.panel__head-link svg {
  width: 14px;
  height: 14px;
}

.recent {
  margin: 0;
  padding: 0;
  list-style: none;
}

.recent__item {
  border-bottom: 1px solid var(--color-border);
}

.recent__item:last-child {
  border-bottom: 0;
}

.recent__link {
  display: block;
  padding: var(--space-4) var(--space-5);
  color: inherit;
  transition: background-color 0.15s ease;
}

.recent__link:hover {
  background: var(--color-surface-hover);
  color: inherit;
}

.recent__link:focus-visible {
  outline-offset: -3px;
  border-radius: 0;
}

.recent__top {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.recent__subject {
  min-width: 0;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 500;
  overflow-wrap: anywhere;
}

.recent__chapter {
  color: var(--color-text-3);
}

.recent__sep {
  margin: 0 var(--space-1);
  color: var(--color-border-strong);
}

.recent__top .tag {
  margin-left: auto;
}

.recent__excerpt {
  margin-top: var(--space-1);
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  overflow: hidden;
}

.recent__excerpt :deep(.markdown-renderer) {
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.recent__excerpt :deep(p) {
  display: -webkit-box;
  overflow: hidden;
  text-wrap: pretty;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.recent__excerpt :deep(.katex-display) {
  display: inline;
  margin: 0;
}

.recent__bottom {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-3);
  margin-top: var(--space-2);
}

.recent__tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-1);
  min-width: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}

.recent__time {
  margin-left: auto;
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 20px;
}

@media (max-width: 767px) {
  .recent__link {
    padding: var(--space-3) var(--space-4);
  }

  .recent__top .tag {
    margin-left: 0;
  }

  .recent__bottom {
    align-items: flex-start;
    flex-direction: column;
  }

  .recent__time {
    margin-left: 0;
  }
}
</style>
