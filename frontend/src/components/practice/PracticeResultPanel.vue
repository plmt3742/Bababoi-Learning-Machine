<script setup lang="ts">
import { computed } from 'vue'
import type { GeneratedQuestion, MasteryStatus } from '../../api/types'
import { masteryStatusLabel, questionTypeLabel } from '../../utils/question'
import {
  calculateAccuracy,
  formatPracticeDuration,
  resolvePracticeQuestionType,
  type PracticeResultItem,
} from '../../utils/practice'

const props = defineProps<{
  results: PracticeResultItem[]
  questions: GeneratedQuestion[]
  masteryStatus: MasteryStatus | null
  masterySyncing: boolean
  masteryError: string
  masterySynced: boolean
}>()

const emit = defineEmits<{
  restart: []
  back: []
  stats: []
  retrySync: []
}>()

const total = computed(() => props.results.length)
const correctCount = computed(() => props.results.filter((item) => item.is_correct).length)
const accuracy = computed(() => calculateAccuracy(correctCount.value, total.value))
const totalDuration = computed(() =>
  props.results.reduce((sum, item) => sum + item.duration_seconds, 0),
)
const totalDurationLabel = computed(() => formatPracticeDuration(totalDuration.value))
const masteryText = computed(() =>
  props.masteryStatus ? masteryStatusLabel(props.masteryStatus) : '',
)
const questionById = computed(
  () => new Map(props.questions.map((question) => [question.id, question])),
)

function displayIndex(index: number): string {
  return String(index + 1).padStart(2, '0')
}

function questionTypeFor(result: PracticeResultItem): string {
  const question = questionById.value.get(result.generated_question_id)
  return question ? questionTypeLabel(resolvePracticeQuestionType(question)) : '练习题'
}
</script>

<template>
  <section class="paper result" aria-labelledby="practice-result-title">
    <div class="result__head">
      <p class="kicker">Practice complete</p>
      <h2 id="practice-result-title">本次练习完成</h2>
      <p>练习记录已保存，结果会计入后续统计；掌握状态按本轮自评同步。</p>
    </div>

    <dl class="result__stats">
      <div class="result-stat">
        <dt>答对</dt>
        <dd>
          <span class="result-stat__value">{{ correctCount }}</span>
          <span class="result-stat__unit">/ {{ total }} 题</span>
        </dd>
      </div>
      <div class="result-stat">
        <dt>正确率</dt>
        <dd>
          <span class="result-stat__value">{{ accuracy }}</span>
          <span class="result-stat__unit">%</span>
        </dd>
      </div>
      <div class="result-stat">
        <dt>总用时</dt>
        <dd>
          <span class="result-stat__value result-stat__value--clock">
            {{ totalDurationLabel }}
          </span>
        </dd>
      </div>
    </dl>

    <div class="result__breakdown">
      <h3>逐题记录</h3>
      <ul class="result-list">
        <li
          v-for="(result, index) in results"
          :key="result.generated_question_id"
          class="result-list__item"
        >
          <span class="result-list__index">{{ displayIndex(index) }}</span>
          <span class="result-list__title">
            {{ questionTypeFor(result) }} · 第 {{ index + 1 }} 题
          </span>
          <span class="result-list__time">
            {{ formatPracticeDuration(result.duration_seconds) }}
          </span>
          <span class="tag" :class="result.is_correct ? 'tag--ok' : 'tag--fail'">
            {{ result.is_correct ? '会' : '不会' }}
          </span>
        </li>
      </ul>
    </div>

    <div
      v-if="masterySyncing || masteryError || (masterySynced && masteryText)"
      class="result__sync"
    >
      <span v-if="masterySyncing" class="muted">正在同步掌握状态…</span>
      <template v-else-if="masteryError">
        <span class="result__sync-error" role="alert">掌握状态未同步：{{ masteryError }}</span>
        <button class="btn btn--quiet btn--sm" type="button" @click="emit('retrySync')">
          重试
        </button>
      </template>
      <span v-else-if="masterySynced && masteryText" class="muted">
        已按本轮自评把错题标记为「{{ masteryText }}」。
      </span>
    </div>

    <div class="result__actions">
      <button class="btn btn--primary" type="button" @click="emit('restart')">再练一次</button>
      <button class="btn btn--outline" type="button" @click="emit('back')">返回错题详情</button>
      <button class="btn btn--quiet" type="button" @click="emit('stats')">去统计</button>
    </div>
  </section>
</template>

<style scoped>
.result {
  overflow: hidden;
  min-width: 0;
}

.result__head {
  padding: var(--space-6) var(--space-6) var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.result__head h2 {
  margin-top: 6px;
  font-size: var(--text-2xl);
  line-height: var(--text-2xl-leading);
  font-weight: 650;
  letter-spacing: -0.012em;
}

.result__head > p:last-child {
  max-width: 56ch;
  margin-top: var(--space-1);
  color: var(--color-text-2);
  font-size: 15px;
  line-height: 24px;
  text-wrap: pretty;
}

.result__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin: 0;
  padding: 0 var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.result-stat {
  min-width: 0;
  padding: var(--space-5) 0;
}

.result-stat + .result-stat {
  padding-left: var(--space-6);
  border-left: 1px solid var(--color-border);
}

.result-stat dt {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.result-stat dd {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin: 2px 0 0;
  min-width: 0;
}

.result-stat__value {
  color: var(--color-text-1);
  font-family: var(--font-math);
  font-size: 34px;
  font-weight: 400;
  line-height: 1.15;
  letter-spacing: -0.01em;
}

.result-stat__value--clock {
  font-family: var(--font-mono);
  font-size: 26px;
  font-weight: 500;
  letter-spacing: 0;
}

.result-stat__unit {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.result__breakdown {
  padding: var(--space-5) var(--space-6) var(--space-3);
}

.result__breakdown h3 {
  font-size: var(--text-base);
  line-height: 24px;
  font-weight: 650;
}

.result-list {
  display: flex;
  flex-direction: column;
  margin: var(--space-3) 0 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--color-border);
}

.result-list__item {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: var(--space-3);
  padding: 10px 0;
  border-bottom: 1px solid var(--color-border);
}

.result-list__item:last-child {
  border-bottom: 0;
}

.result-list__index {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.result-list__title {
  min-width: 0;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  overflow-wrap: anywhere;
}

.result-list__time {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.result__sync {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-2);
  margin: 0 var(--space-6);
  padding: 10px var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
}

.result__sync-error {
  color: var(--color-danger-text);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.result__actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding: var(--space-5) var(--space-6) var(--space-6);
}

@media (max-width: 767px) {
  .result__head {
    padding: var(--space-5) var(--space-4);
  }

  .result__head h2 {
    font-size: 24px;
    line-height: 32px;
  }

  .result__head > p:last-child {
    font-size: var(--text-sm);
    line-height: var(--text-sm-leading);
  }

  .result__stats {
    padding: 0 var(--space-4);
  }

  .result-stat {
    padding: var(--space-4) 0;
  }

  .result-stat + .result-stat {
    padding-left: var(--space-4);
  }

  .result-stat__value {
    font-size: 28px;
  }

  .result-stat__value--clock {
    font-size: 20px;
  }

  .result__breakdown {
    padding: var(--space-4) var(--space-4) var(--space-2);
  }

  .result-list__item {
    grid-template-columns: 28px minmax(0, 1fr) auto auto;
    gap: var(--space-2);
  }

  .result__sync {
    margin: 0 var(--space-4);
  }

  .result__actions {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    padding: var(--space-4);
  }

  .result__actions .btn {
    width: 100%;
    min-height: 42px;
  }
}
</style>
