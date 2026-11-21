<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import '@arco-design/web-vue/es/message/style/css.js'
import { IconCheck } from '@arco-design/web-vue/es/icon'
import MarkdownRenderer from '../../common/MarkdownRenderer.vue'
import { circledIndex, toggleImageSelection } from '../../../utils/imageIntake'
import type { GeneratedImageTask, SavedImageQuestion } from '../../../utils/imageIntake'
import { questionTypeLabel } from '../../../utils/question'

const props = defineProps<{
  saved: SavedImageQuestion[]
  generating: boolean
  tasks: GeneratedImageTask[]
  error: string
}>()

const emit = defineEmits<{
  generate: [questionIds: number[]]
  'go-tasks': []
  'open-question': [questionId: number]
}>()

const selected = ref<number[]>([])

const generatedIds = computed(() => new Set(props.tasks.map((task) => task.questionId)))
const pendingSelection = computed(() =>
  selected.value.filter((questionId) => !generatedIds.value.has(questionId)),
)
const allSelected = computed(
  () => props.saved.length > 0 && selected.value.length === props.saved.length,
)

const generateLabel = computed(() => {
  if (props.generating) return '正在创建任务…'
  if (selected.value.length > 0 && pendingSelection.value.length === 0) return '已创建生成任务'
  return '生成相似题'
})

watch(
  () => props.saved.map((entry) => entry.question.id),
  (ids) => {
    selected.value = selected.value.filter((questionId) => ids.includes(questionId))
  },
)

function toggleSelection(questionId: number, value: unknown): void {
  selected.value = toggleImageSelection(selected.value, questionId, value)
}

function handleAllSelected(value: unknown): void {
  selected.value = value === true ? props.saved.map((entry) => entry.question.id) : []
}

function savedIndex(questionId: number): number {
  return props.saved.findIndex((entry) => entry.question.id === questionId)
}

function taskFor(questionId: number): GeneratedImageTask | undefined {
  return props.tasks.find((task) => task.questionId === questionId)
}

function handleGenerate(): void {
  if (props.generating) return
  if (selected.value.length === 0) {
    Message.warning('请选择至少 1 道题生成相似题')
    return
  }
  if (pendingSelection.value.length === 0) {
    Message.info('所选题目已创建生成任务')
    return
  }
  emit('generate', pendingSelection.value)
}

function openFirst(): void {
  const first = props.saved[0]
  if (first) emit('open-question', first.question.id)
}
</script>

<template>
  <section
    id="image-saved-panel"
    class="panel"
    tabindex="-1"
    aria-labelledby="image-saved-heading"
  >
    <div class="panel__head">
      <h2 id="image-saved-heading">已保存的题目</h2>
      <span class="tag tag--ok">
        <span class="dot" aria-hidden="true" />
        {{ saved.length }} 道
      </span>
      <p class="panel__head-hint">选择题目生成相似题</p>
    </div>

    <div class="panel__body">
      <p class="saved-intro">
        已保存 {{ saved.length }} 道，选择题目生成相似题；每题生成 3 段（3 道相似题），超出并发会自动排队。
      </p>

      <div class="saved-toolbar">
        <a-checkbox
          :model-value="allSelected"
          :indeterminate="selected.length > 0 && !allSelected"
          @update:model-value="handleAllSelected"
        >
          全选
        </a-checkbox>
        <span class="saved-toolbar__count">已选 {{ selected.length }} / {{ saved.length }} 道</span>
      </div>

      <ul class="saved-list">
        <li v-for="(entry, index) in saved" :key="entry.question.id" class="saved-row">
          <a-checkbox
            :model-value="selected.includes(entry.question.id)"
            :aria-label="`选择第 ${index + 1} 道题生成相似题`"
            @update:model-value="toggleSelection(entry.question.id, $event)"
          />

          <div class="saved-row__body">
            <div class="saved-row__meta">
              <span class="saved-row__index" aria-hidden="true">{{ circledIndex(index + 1) }}</span>
              <span class="tag">{{ questionTypeLabel(entry.question.question_type) }}</span>
              <span v-if="taskFor(entry.question.id)" class="tag tag--run">
                已创建生成任务
              </span>
            </div>

            <div class="saved-row__content">
              <MarkdownRenderer :content="entry.question.content_md" compact />
            </div>

            <button
              class="btn btn--quiet btn--sm"
              type="button"
              @click="emit('open-question', entry.question.id)"
            >
              查看题目
            </button>
          </div>
        </li>
      </ul>

      <div class="generate-bar">
        <p class="generate-bar__hint">
          每题生成 3 段（3 道相似题），超出并发会自动排队。
        </p>
        <button
          class="btn btn--primary"
          type="button"
          :disabled="generating || pendingSelection.length === 0"
          :aria-busy="generating"
          @click="handleGenerate"
        >
          <IconCheck aria-hidden="true" />
          {{ generateLabel }}
        </button>
      </div>

      <div v-if="tasks.length" class="task-result">
        <p class="task-result__title">
          已创建 {{ tasks.reduce((count, task) => count + task.taskIds.length, 0) }} 个生成任务
        </p>
        <div class="task-result__chips">
          <template v-for="task in tasks" :key="task.questionId">
            <span class="tag tag--run">
              第 {{ savedIndex(task.questionId) + 1 }} 道 · 已创建 {{ task.taskIds.length }} 段生成任务
            </span>
          </template>
        </div>
        <div class="task-result__actions">
          <button class="btn btn--outline btn--sm" type="button" @click="emit('go-tasks')">
            去任务中心
          </button>
          <button class="btn btn--outline btn--sm" type="button" @click="openFirst">
            查看第一道题
          </button>
        </div>
      </div>

      <p v-if="error" class="field-error" role="alert">{{ error }}</p>
    </div>
  </section>
</template>

<style scoped>
.saved-intro {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

#image-saved-panel {
  scroll-margin-top: var(--space-6);
}

#image-saved-panel:focus {
  outline: none;
}

.saved-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

.saved-toolbar__count {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.saved-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: var(--space-4) 0 0;
  list-style: none;
}

.saved-row {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
}

.saved-row > :deep(.arco-checkbox) {
  flex: none;
  margin-top: 2px;
}

.saved-row__body {
  min-width: 0;
  flex: 1;
}

.saved-row__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-2);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.saved-row__index {
  color: var(--color-primary-active);
  font-family: var(--font-math);
  font-size: var(--text-base);
  line-height: 1;
}

.saved-row__content {
  margin-top: 6px;
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  overflow-wrap: anywhere;
  text-wrap: pretty;
}

.saved-row__body .btn {
  margin-top: var(--space-1);
  padding-left: 0;
}

.generate-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.generate-bar__hint {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.generate-bar__hint strong {
  color: var(--color-text-1);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.task-result {
  margin-top: var(--space-4);
  padding: var(--space-3);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-md);
  background: var(--color-primary-softer);
}

.task-result__title {
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 650;
}

.task-result__chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.task-result__chips .tag {
  height: auto;
  min-height: 26px;
  padding: 3px 8px;
  white-space: normal;
  line-height: 18px;
}

.task-result__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

@media (max-width: 767px) {
  .saved-row {
    gap: var(--space-2);
  }

  .generate-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .generate-bar .btn {
    width: 100%;
  }
}
</style>
