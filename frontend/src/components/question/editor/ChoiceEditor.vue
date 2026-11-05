<script setup lang="ts">
import { computed } from 'vue'
import { IconDelete, IconPlus } from '@arco-design/web-vue/es/icon'
import {
  createChoiceOption,
  MAX_CHOICE_OPTIONS,
  MAX_OPTION_CONTENT_LENGTH,
  MIN_CHOICE_OPTIONS,
  optionLabel,
  validateChoiceOptions,
} from '../../../utils/questionEditor'
import type { ChoiceOptionDraft } from '../../../utils/questionEditor'

const props = defineProps<{
  options: ChoiceOptionDraft[]
  correctLabel: string
  showValidation: boolean
}>()

const emit = defineEmits<{
  'update:options': [value: ChoiceOptionDraft[]]
  'update:correctLabel': [value: string]
}>()

const optionRows = computed(() =>
  props.options.map((option, index) => ({
    index,
    label: optionLabel(index),
    content_md: option.content_md,
  })),
)

const labelOptions = computed(() =>
  optionRows.value.map((row) => ({ label: `选项 ${row.label}`, value: row.label })),
)

const optionError = computed(() => validateChoiceOptions(props.options))
const canRemove = computed(() => props.options.length > MIN_CHOICE_OPTIONS)
const canAdd = computed(() => props.options.length < MAX_CHOICE_OPTIONS)

function updateOption(index: number, contentMd: string): void {
  emit(
    'update:options',
    props.options.map((option, position) =>
      position === index ? { content_md: contentMd } : { content_md: option.content_md },
    ),
  )
}

function handleOptionInput(index: number, value: unknown): void {
  updateOption(index, typeof value === 'string' ? value : '')
}

function addOption(): void {
  if (!canAdd.value) return
  emit('update:options', [...props.options, createChoiceOption()])
}

function removeOption(index: number): void {
  if (!canRemove.value) return
  emit(
    'update:options',
    props.options.filter((_option, position) => position !== index),
  )
}

function handleCorrectLabel(value: unknown): void {
  emit('update:correctLabel', typeof value === 'string' ? value : '')
}
</script>

<template>
  <div class="choice-editor">
    <div class="choice-editor__intro">
      <p class="field-label">选项内容</p>
      <p class="choice-editor__hint">
        按顺序自动编号 A、B、C…，至少 {{ MIN_CHOICE_OPTIONS }} 项，最多
        {{ MAX_CHOICE_OPTIONS }} 项。
      </p>
    </div>

    <ol class="choice-list">
      <li v-for="row in optionRows" :key="row.index" class="choice-row">
        <div class="choice-row__head">
          <span class="choice-row__badge" aria-hidden="true">{{ row.label }}</span>
          <label class="choice-row__caption" :for="`choice-option-${row.index}`">
            选项 {{ row.label }}
          </label>
          <button
            class="btn btn--ghost btn--sm choice-row__remove"
            type="button"
            :disabled="!canRemove"
            :aria-label="`删除选项 ${row.label}`"
            @click="removeOption(row.index)"
          >
            <IconDelete aria-hidden="true" />
            删除
          </button>
        </div>

        <a-textarea
          :model-value="row.content_md"
          :auto-size="{ minRows: 2, maxRows: 6 }"
          :max-length="MAX_OPTION_CONTENT_LENGTH"
          :placeholder="`选项 ${row.label} 的内容，支持 Markdown / LaTeX`"
          :textarea-attrs="{ id: `choice-option-${row.index}` }"
          @update:model-value="handleOptionInput(row.index, $event)"
        />

        <p v-if="showValidation && !row.content_md.trim()" class="field-error">
          选项 {{ row.label }} 还没有填写内容
        </p>
      </li>
    </ol>

    <div class="choice-actions">
      <button class="btn btn--outline btn--sm" type="button" :disabled="!canAdd" @click="addOption">
        <IconPlus aria-hidden="true" />
        添加选项
      </button>
      <span class="choice-actions__count">
        {{ options.length }} / {{ MAX_CHOICE_OPTIONS }} 个选项
      </span>
    </div>

    <div class="choice-answer">
      <label class="field-label" for="choice-correct">正确答案</label>
      <a-select
        id="choice-correct"
        :model-value="correctLabel"
        :options="labelOptions"
        placeholder="选择正确选项（可选）"
        allow-clear
        aria-label="正确答案"
        @update:model-value="handleCorrectLabel"
      />
      <p class="choice-answer__hint">选择后会自动填入答案「选 A」；仍可在上方答案框中手动修改。</p>
    </div>

    <p v-if="showValidation && optionError" class="field-error choice-error" role="alert">
      {{ optionError }}
    </p>
  </div>
</template>

<style scoped>
.choice-editor {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.choice-editor__intro {
  margin-bottom: var(--space-3);
}

.choice-editor__intro .field-label {
  margin-bottom: 2px;
}

.choice-editor__hint,
.choice-answer__hint {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.choice-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  list-style: none;
}

.choice-row {
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
}

.choice-row__head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.choice-row__badge {
  display: grid;
  place-items: center;
  flex: none;
  width: 26px;
  height: 26px;
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-sm);
  background: var(--color-primary-soft);
  color: var(--color-primary-active);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 1;
  font-weight: 650;
}

.choice-row__caption {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 600;
}

.choice-row__remove {
  margin-left: auto;
}

.choice-row :deep(.arco-textarea-wrapper) {
  border-radius: var(--radius-md);
}

.choice-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-3);
}

.choice-actions__count {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-variant-numeric: tabular-nums;
}

.choice-answer {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px dashed var(--color-border-strong);
}

.choice-answer .field-label {
  margin-bottom: 6px;
}

.choice-answer__hint {
  margin-top: 6px;
}

.choice-error {
  margin-top: var(--space-3);
}

@media (max-width: 560px) {
  .choice-row__head {
    flex-wrap: wrap;
  }

  .choice-row__remove {
    margin-left: 0;
  }
}
</style>
