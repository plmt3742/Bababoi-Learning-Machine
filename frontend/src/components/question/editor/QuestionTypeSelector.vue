<script setup lang="ts">
import type { QuestionType } from '../../../api/types'

defineProps<{
  modelValue: QuestionType
}>()

const emit = defineEmits<{
  'update:modelValue': [value: QuestionType]
}>()

const TYPE_OPTIONS: Array<{ value: QuestionType; label: string; hint: string }> = [
  { value: 'solve', label: '解答题', hint: '完整作答，保留原题结构' },
  { value: 'choice', label: '选择题', hint: '2–6 个选项，自动编号' },
  { value: 'blank', label: '填空题', hint: '用 ___ 标记每个空位' },
]
</script>

<template>
  <div class="type-select" role="radiogroup" aria-label="题型">
    <button
      v-for="option in TYPE_OPTIONS"
      :key="option.value"
      class="type-select__option"
      type="button"
      role="radio"
      :aria-checked="modelValue === option.value"
      @click="emit('update:modelValue', option.value)"
    >
      <span class="type-select__label">{{ option.label }}</span>
      <span class="type-select__hint">{{ option.hint }}</span>
    </button>
  </div>
</template>

<style scoped>
.type-select {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-2);
}

.type-select__option {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 3px;
  min-height: 66px;
  padding: 10px var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-2);
  text-align: left;
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.type-select__option:hover {
  border-color: var(--color-text-3);
  background: var(--color-surface-hover);
}

.type-select__option[aria-checked='true'] {
  border-color: var(--color-primary);
  background: var(--color-primary-softer);
  box-shadow: inset 0 0 0 1px var(--color-primary);
  color: var(--color-text-1);
}

.type-select__label {
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 650;
}

.type-select__hint {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

@media (max-width: 560px) {
  .type-select {
    grid-template-columns: minmax(0, 1fr);
  }

  .type-select__option {
    min-height: 0;
  }
}
</style>
