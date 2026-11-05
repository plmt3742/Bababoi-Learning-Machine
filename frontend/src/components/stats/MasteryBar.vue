<script setup lang="ts">
import { computed } from 'vue'
import { percentOf } from '../../utils/stats'

type MasteryKey = 'mastered' | 'reviewing' | 'unmastered'

interface MasteryRow {
  key: MasteryKey
  label: string
  count: number
}

const props = defineProps<{
  mastered: number
  reviewing: number
  unmastered: number
}>()

const rows = computed<MasteryRow[]>(() => [
  { key: 'mastered', label: '已掌握', count: Math.max(0, props.mastered) },
  { key: 'reviewing', label: '复习中', count: Math.max(0, props.reviewing) },
  { key: 'unmastered', label: '未掌握', count: Math.max(0, props.unmastered) },
])

const total = computed(() => rows.value.reduce((sum, row) => sum + row.count, 0))
const hasData = computed(() => total.value > 0)

const barLabel = computed(
  () =>
    `掌握度分布：已掌握 ${rows.value[0].count} 道，复习中 ${rows.value[1].count} 道，未掌握 ${rows.value[2].count} 道`,
)

function widthPercent(count: number): string {
  return `${percentOf(count, total.value)}%`
}

function percentage(count: number): string {
  return `${Math.round(percentOf(count, total.value))}%`
}
</script>

<template>
  <div class="mastery">
    <div class="mastery__bar" role="img" :aria-label="barLabel">
      <span
        v-for="row in rows"
        :key="row.key"
        class="mastery__segment"
        :class="`mastery__segment--${row.key}`"
        :style="{ width: widthPercent(row.count) }"
      ></span>
    </div>

    <ul class="mastery__rows">
      <li v-for="row in rows" :key="row.key" class="mastery__row">
        <span class="mastery__dot" :class="`mastery__dot--${row.key}`" aria-hidden="true"></span>
        <span class="mastery__label">{{ row.label }}</span>
        <span class="mastery__count">{{ row.count }}</span>
        <span class="mastery__pct">{{ percentage(row.count) }}</span>
      </li>
    </ul>

    <p v-if="!hasData" class="mastery__empty">还没有错题，录入后会展示掌握度分布。</p>
  </div>
</template>

<style scoped>
.mastery {
  display: flex;
  flex-direction: column;
}

.mastery__bar {
  display: flex;
  height: 10px;
  overflow: hidden;
  border-radius: var(--radius-sm);
  background: var(--color-fill);
}

.mastery__segment {
  height: 100%;
  flex: none;
  transition: width 0.3s ease;
}

.mastery__segment--mastered {
  background: var(--color-success);
}

.mastery__segment--reviewing {
  background: var(--color-warning);
}

.mastery__segment--unmastered {
  background: var(--color-danger);
}

.mastery__rows {
  margin: var(--space-3) 0 0;
  padding: 0;
  list-style: none;
}

.mastery__row {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr) auto 46px;
  align-items: center;
  gap: var(--space-2);
  padding: 10px 0;
  border-bottom: 1px solid var(--color-border);
}

.mastery__row:last-child {
  border-bottom: 0;
}

.mastery__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.mastery__dot--mastered {
  background: var(--color-success);
}

.mastery__dot--reviewing {
  background: var(--color-warning);
}

.mastery__dot--unmastered {
  background: var(--color-danger);
}

.mastery__label {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.mastery__count {
  color: var(--color-text-1);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.mastery__pct {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.mastery__empty {
  margin-top: var(--space-3);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}
</style>
