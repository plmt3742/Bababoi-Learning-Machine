<script setup lang="ts">
import { computed, watch } from 'vue'
import { IconDelete, IconPlus } from '@arco-design/web-vue/es/icon'
import {
  createBlankAnswer,
  countBlankMarkers,
  insertBlankMarker,
  MAX_ANSWER_CONTENT_LENGTH,
  MAX_BLANK_MARKERS,
  removeBlankMarkerAt,
  syncBlankAnswers,
  validateBlankAnswers,
} from '../../../utils/questionEditor'
import type { BlankAnswerDraft } from '../../../utils/questionEditor'

const props = defineProps<{
  content: string
  blanks: BlankAnswerDraft[]
  showValidation: boolean
}>()

const emit = defineEmits<{
  'update:content': [value: string]
  'update:blanks': [value: BlankAnswerDraft[]]
}>()

const markerCount = computed(() => countBlankMarkers(props.content))
const blankError = computed(() => validateBlankAnswers(props.content, props.blanks))
const canAdd = computed(() => markerCount.value < MAX_BLANK_MARKERS)
const canRemove = computed(() => markerCount.value > 1)

watch(
  markerCount,
  (count) => {
    if (props.blanks.length === count) return
    emit('update:blanks', syncBlankAnswers(props.content, props.blanks))
  },
  { immediate: true },
)

function handleAnswerInput(index: number, value: unknown): void {
  const answerMd = typeof value === 'string' ? value : ''

  emit(
    'update:blanks',
    props.blanks.map((blank, position) =>
      position === index ? { answer_md: answerMd } : { answer_md: blank.answer_md },
    ),
  )
}

function addBlank(): void {
  if (!canAdd.value) return

  emit('update:content', insertBlankMarker(props.content))
  emit('update:blanks', [...props.blanks, createBlankAnswer()])
}

function removeBlank(index: number): void {
  if (!canRemove.value) return

  emit('update:content', removeBlankMarkerAt(props.content, index))
  emit(
    'update:blanks',
    props.blanks.filter((_blank, position) => position !== index),
  )
}
</script>

<template>
  <div class="blank-editor">
    <div class="blank-status">
      <span class="tag" :class="markerCount > 0 ? 'tag--ok' : 'tag--fail'">
        <span class="dot" aria-hidden="true" />
        检测到 {{ markerCount }} 个空位
      </span>
      <span class="blank-status__hint">连续 3 个及以上下划线 ___ 视为一个空位。</span>
    </div>

    <p v-if="!blanks.length" class="blank-empty">
      题干中还没有空位。在题干里写 ___，或点击下方按钮插入第一个空位。
    </p>

    <ol v-else class="blank-list">
      <li v-for="(blank, index) in blanks" :key="index" class="blank-row">
        <div class="blank-row__head">
          <span class="blank-row__badge" aria-hidden="true">{{ index + 1 }}</span>
          <label class="blank-row__caption" :for="`blank-answer-${index}`">
            第 {{ index + 1 }} 空
          </label>
          <span class="blank-row__marker">对应题干第 {{ index + 1 }} 处 ___</span>
          <button
            class="btn btn--ghost btn--sm blank-row__remove"
            type="button"
            :disabled="!canRemove"
            :aria-label="`删除第 ${index + 1} 空`"
            @click="removeBlank(index)"
          >
            <IconDelete aria-hidden="true" />
            删除
          </button>
        </div>

        <a-textarea
          :model-value="blank.answer_md"
          :auto-size="{ minRows: 2, maxRows: 5 }"
          :max-length="MAX_ANSWER_CONTENT_LENGTH"
          :placeholder="`第 ${index + 1} 空的答案，支持 Markdown / LaTeX`"
          :textarea-attrs="{ id: `blank-answer-${index}` }"
          @update:model-value="handleAnswerInput(index, $event)"
        />

        <p v-if="showValidation && !blank.answer_md.trim()" class="field-error">
          第 {{ index + 1 }} 空还没有填写答案
        </p>
      </li>
    </ol>

    <div class="blank-actions">
      <button class="btn btn--outline btn--sm" type="button" :disabled="!canAdd" @click="addBlank">
        <IconPlus aria-hidden="true" />
        插入空位
      </button>
      <span class="blank-actions__count"> {{ markerCount }} / {{ MAX_BLANK_MARKERS }} 个空位 </span>
    </div>

    <p class="blank-actions__hint">
      插入空位会在题干末尾追加 ___，并同步新增一条答案；删除空位会同时移除对应的 ___。
    </p>

    <p v-if="showValidation && blankError" class="field-error blank-error" role="alert">
      {{ blankError }}
    </p>
  </div>
</template>

<style scoped>
.blank-editor {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.blank-status {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-3);
}

.blank-status__hint {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.blank-empty {
  margin-top: var(--space-3);
  padding: var(--space-3);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.blank-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: var(--space-3) 0 0;
  list-style: none;
}

.blank-row {
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
}

.blank-row__head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-2);
  margin-bottom: var(--space-2);
}

.blank-row__badge {
  display: grid;
  place-items: center;
  flex: none;
  width: 26px;
  height: 26px;
  border: 1px solid var(--color-primary-border);
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary-active);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 1;
  font-weight: 650;
}

.blank-row__caption {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 600;
}

.blank-row__marker {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.blank-row__remove {
  margin-left: auto;
}

.blank-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-3);
}

.blank-actions__count {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-variant-numeric: tabular-nums;
}

.blank-actions__hint {
  margin-top: var(--space-2);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.blank-error {
  margin-top: var(--space-3);
}

@media (max-width: 560px) {
  .blank-row__remove {
    margin-left: 0;
  }
}
</style>
