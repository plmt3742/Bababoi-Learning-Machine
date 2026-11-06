<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import '@arco-design/web-vue/es/message/style/css.js'
import { IconCheck } from '@arco-design/web-vue/es/icon'
import { circledIndex, MAX_GENERATE_SELECTION } from '../../../utils/imageIntake'
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
  if (value !== true) {
    selected.value = selected.value.filter((id) => id !== questionId)
    return
  }
  if (selected.value.includes(questionId)) return
  if (selected.value.length >= MAX_GENERATE_SELECTION) {
    Message.warning(`最多选择 ${MAX_GENERATE_SELECTION} 道题生成相似题`)
    return
  }
  selected.value = [...selected.value, questionId]
}

function taskFor(questionId: number): GeneratedImageTask | undefined {
  return props.tasks.find((task) => task.questionId === questionId)
}

function handleGenerate(): void {
  if (props.generating) return
  if (selected.value.length === 0) {
    Message.warning('请选择 1–3 道题生成相似题')
    return
  }
  if (selected.value.length > MAX_GENERATE_SELECTION) {
    Message.error(`最多选择 ${MAX_GENERATE_SELECTION} 道题生成相似题`)
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

function excerpt(content: string, limit = 96): string {
  const compact = content.replace(/\s+/g, ' ').trim()
  return compact.length <= limit ? compact : `${compact.slice(0, limit)}…`
}
</script>

<template>
  <section id="image-saved-panel" class="panel" aria-labelledby="image-saved-heading">
    <div class="panel__head">
      <h2 id="image-saved-heading">已保存的题目</h2>
      <span class="tag tag--ok">
        <span class="dot" aria-hidden="true" />
        {{ saved.length }} 道
      </span>
      <p class="panel__head-hint">选择 1–3 道生成相似题</p>
    </div>

    <div class="panel__body">
      <p class="saved-intro">
        已保存 {{ saved.length }} 道，选择 1–3 道生成相似题；每道题会创建独立的生成任务。
      </p>

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
              <span>题目 #{{ entry.question.id }}</span>
              <span>分析任务 #{{ entry.taskId }}</span>
              <span v-if="taskFor(entry.question.id)" class="tag tag--run">
                生成任务 #{{ taskFor(entry.question.id)?.taskIds[0] }}
                <template v-if="(taskFor(entry.question.id)?.taskIds.length ?? 0) > 1">
                  等 {{ taskFor(entry.question.id)?.taskIds.length }} 个
                </template>
              </span>
            </div>

            <p class="saved-row__content">{{ excerpt(entry.question.content_md) }}</p>

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
          已选 <strong>{{ selected.length }}</strong> / {{ MAX_GENERATE_SELECTION }}
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
            <span v-for="taskId in task.taskIds" :key="taskId" class="tag tag--run">
              任务 #{{ taskId }} · 题目 #{{ task.questionId }}
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
