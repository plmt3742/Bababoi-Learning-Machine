<script setup lang="ts">
import { computed } from 'vue'
import MarkdownRenderer from '../../common/MarkdownRenderer.vue'
import { buildBlankPreview, countBlankMarkers, optionLabel } from '../../../utils/questionEditor'
import type { ChoiceOptionDraft } from '../../../utils/questionEditor'
import type { QuestionType } from '../../../api/types'

const props = defineProps<{
  content: string
  questionType: QuestionType
  options: ChoiceOptionDraft[]
  correctLabel: string
}>()

const displayContent = computed(() =>
  props.questionType === 'blank' ? buildBlankPreview(props.content) : props.content,
)

const optionRows = computed(() =>
  props.options.map((option, index) => ({
    label: optionLabel(index),
    content_md: option.content_md,
  })),
)

const markerCount = computed(() => countBlankMarkers(props.content))
</script>

<template>
  <div class="question-preview">
    <MarkdownRenderer :content="displayContent" />

    <ol v-if="questionType === 'choice'" class="preview-options">
      <li v-for="row in optionRows" :key="row.label" class="preview-options__item">
        <span class="preview-options__label" aria-hidden="true">{{ row.label }}</span>
        <div class="preview-options__body">
          <MarkdownRenderer v-if="row.content_md.trim()" :content="row.content_md" compact />
          <p v-else class="preview-options__empty">选项 {{ row.label }} 尚未填写</p>
        </div>
      </li>
    </ol>

    <div v-if="questionType === 'blank'" class="preview-blanks">
      <span class="tag" :class="markerCount > 0 ? 'tag--ok' : 'tag--fail'">
        <span class="dot" aria-hidden="true" />
        {{ markerCount }} 个空位
      </span>
      <span class="preview-blanks__hint">题干中的 ___ 是待填写的空位</span>
    </div>

    <div v-if="questionType === 'choice' && correctLabel" class="preview-answer">
      <span class="tag tag--run">正确答案 {{ correctLabel }}</span>
      <span class="preview-answer__hint">预览仅显示结构，答案以「答案与解析」为准</span>
    </div>
  </div>
</template>

<style scoped>
.question-preview {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.preview-options {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding-top: var(--space-3);
  border-top: 1px dashed var(--color-border-strong);
  list-style: none;
}

.preview-options__item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
}

.preview-options__label {
  display: grid;
  place-items: center;
  flex: none;
  width: 26px;
  height: 26px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 1;
  font-weight: 650;
}

.preview-options__body {
  min-width: 0;
  flex: 1;
}

.preview-options__empty {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-style: italic;
}

.preview-blanks,
.preview-answer {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px dashed var(--color-border-strong);
}

.preview-blanks__hint,
.preview-answer__hint {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}
</style>
