<script setup lang="ts">
import { computed, watch } from 'vue'
import { IconDelete } from '@arco-design/web-vue/es/icon'
import BlankEditor from '../editor/BlankEditor.vue'
import ChoiceEditor from '../editor/ChoiceEditor.vue'
import QuestionTypeSelector from '../editor/QuestionTypeSelector.vue'
import {
  circledIndex,
  ensureItemStructure,
  MAX_IMAGE_CONTENT_LENGTH,
  validateImageItem,
} from '../../../utils/imageIntake'
import type { ImageItemDraft } from '../../../utils/imageIntake'
import { optionLabel } from '../../../utils/questionEditor'
import { difficultyLabel, questionTypeLabel } from '../../../utils/question'
import type { QuestionType } from '../../../api/types'

const props = defineProps<{
  item: ImageItemDraft
  position: number
  showValidation: boolean
  disabled: boolean
}>()

const emit = defineEmits<{
  remove: []
  update: [item: ImageItemDraft]
}>()

const validationMessage = computed(() => {
  if (!props.item.content_md.trim()) return '题干不能为空'
  if (props.item.content_md.length > MAX_IMAGE_CONTENT_LENGTH) {
    return `题干不能超过 ${MAX_IMAGE_CONTENT_LENGTH} 个字符`
  }
  if (props.item.question_type === 'solve') return validateImageItem(props.item)
  return null
})

function patch(changes: Partial<ImageItemDraft>): void {
  emit('update', { ...props.item, ...changes })
}

function changeType(value: QuestionType): void {
  const next = { ...props.item, question_type: value }
  ensureItemStructure(next)
  emit('update', next)
}

function handleContent(value: unknown): void {
  if (typeof value !== 'string') return
  patch({ content_md: value })
}

function handleChapter(value: unknown): void {
  patch({ chapter: typeof value === 'string' ? value : '' })
}

function handleSelected(value: unknown): void {
  patch({ selected: value === true })
}

watch(
  () => props.item.options.length,
  () => {
    if (!props.item.correct_label) return
    const exists = props.item.options.some(
      (_option, index) => optionLabel(index) === props.item.correct_label,
    )
    if (!exists) patch({ correct_label: '' })
  },
)
</script>

<template>
  <article :id="`image-item-${item.key}`" class="item-card">
    <fieldset class="item-fieldset" :disabled="disabled">
      <legend class="sr-only">第 {{ position }} 道提取结果</legend>

      <div class="item-head">
        <span class="item-index" aria-hidden="true">{{ circledIndex(position) }}</span>
        <span class="tag">{{ questionTypeLabel(item.question_type) }}</span>
        <span v-if="item.subject" class="tag tag--point">学科：{{ item.subject }}</span>
        <span v-if="item.difficulty" class="tag">难度：{{ difficultyLabel(item.difficulty) }}</span>
        <span v-if="item.incomplete" class="tag tag--fail">
          <span class="dot" aria-hidden="true" />
          信息不完整
        </span>
        <span v-if="item.has_figure" class="tag tag--reviewing">含图 · 仅文字</span>

        <div class="item-head__actions">
          <a-checkbox :model-value="item.selected" @update:model-value="handleSelected">
            保存这道题
          </a-checkbox>
          <button
            class="btn btn--ghost btn--sm"
            type="button"
            :aria-label="`删除第 ${position} 道题`"
            @click="emit('remove')"
          >
            <IconDelete aria-hidden="true" />
            删除
          </button>
        </div>
      </div>

      <div v-if="item.warnings.length" class="item-warnings">
        <span v-for="warning in item.warnings" :key="warning" class="tag tag--draft">
          {{ warning }}
        </span>
      </div>

      <div class="item-field">
        <label class="field-label" :for="`image-content-${item.key}`">题干</label>
        <a-textarea
          :model-value="item.content_md"
          :auto-size="{ minRows: 3, maxRows: 12 }"
          :max-length="MAX_IMAGE_CONTENT_LENGTH"
          :textarea-attrs="{ id: `image-content-${item.key}` }"
          placeholder="提取出的题干，可在这里直接修改；公式用 $...$ 包裹"
          @update:model-value="handleContent"
        />
        <div class="item-meta">
          <span>支持 Markdown；公式用 $...$ 或 $$...$$ 包裹</span>
          <span class="item-meta__count">
            {{ item.content_md.length }} / {{ MAX_IMAGE_CONTENT_LENGTH }}
          </span>
        </div>
      </div>

      <div class="item-field">
        <p class="field-label">题型</p>
        <QuestionTypeSelector :model-value="item.question_type" @update:model-value="changeType" />
      </div>

      <div class="item-field">
        <label class="field-label" :for="`image-chapter-${item.key}`">章节（可选）</label>
        <a-input
          :model-value="item.chapter"
          :max-length="100"
          :input-attrs="{ id: `image-chapter-${item.key}` }"
          placeholder="AI 初判章节，可修改"
          allow-clear
          @update:model-value="handleChapter"
        />
      </div>

      <ChoiceEditor
        v-if="item.question_type === 'choice'"
        :options="item.options"
        :correct-label="item.correct_label"
        :show-validation="showValidation"
        @update:options="patch({ options: $event })"
        @update:correct-label="patch({ correct_label: $event })"
      />

      <BlankEditor
        v-else-if="item.question_type === 'blank'"
        :content="item.content_md"
        :blanks="item.blanks"
        :show-validation="showValidation"
        @update:content="patch({ content_md: $event })"
        @update:blanks="patch({ blanks: $event })"
      />

      <p v-else class="info-note">
        解答题按完整题干保存；小问可用 Markdown 编号表达，不需要额外选项或空位。
      </p>

      <p v-if="showValidation && validationMessage" class="field-error" role="alert">
        {{ validationMessage }}
      </p>
      <p v-else-if="item.saveError" class="field-error" role="alert">{{ item.saveError }}</p>
    </fieldset>
  </article>
</template>

<style scoped>
.item-card {
  min-width: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface-subtle);
}

.item-fieldset {
  min-width: 0;
  margin: 0;
  padding: var(--space-4);
  border: 0;
}

.item-fieldset:disabled {
  opacity: 0.72;
}

.item-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.item-index {
  display: grid;
  place-items: center;
  flex: none;
  width: 30px;
  height: 30px;
  border: 1px solid var(--color-primary-border);
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary-active);
  font-family: var(--font-math);
  font-size: var(--text-base);
  line-height: 1;
}

.item-head__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-left: auto;
}

.item-warnings {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-warning-border);
  border-radius: var(--radius-md);
  background: var(--color-warning-soft);
}

.item-warnings .tag {
  height: auto;
  min-height: 26px;
  padding: 3px 8px;
  white-space: normal;
  line-height: 18px;
  text-wrap: pretty;
}

.item-field {
  margin-top: var(--space-4);
}

.item-field .field-label {
  margin-bottom: 6px;
}

.item-meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
  margin-top: 6px;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.item-meta__count {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.item-card :deep(.arco-form-item) {
  margin-bottom: 0;
}

.info-note {
  margin-top: var(--space-4);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

@media (max-width: 767px) {
  .item-fieldset {
    padding: var(--space-3);
  }

  .item-head__actions {
    width: 100%;
    margin-left: 0;
    justify-content: space-between;
  }

  .item-meta {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
