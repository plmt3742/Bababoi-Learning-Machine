<script setup lang="ts">
import { computed } from 'vue'
import type { StatsTrendPoint } from '../../api/types'
import {
  formatAccuracy,
  formatTrendDay,
  formatTrendDayShort,
  summarizeTrend,
} from '../../utils/stats'

const props = defineProps<{
  points: StatsTrendPoint[]
}>()

const totals = computed(() => summarizeTrend(props.points))
const maxCount = computed(() =>
  Math.max(0, ...props.points.map((point) => Math.max(0, point.practice_count))),
)
const hasData = computed(() => totals.value.practiceCount > 0)

const chartLabel = computed(() => {
  if (!hasData.value) return '近 7 天练习趋势：暂无练习记录'
  return `近 7 天练习趋势：练习 ${totals.value.practiceCount} 次，答对 ${
    totals.value.correctCount
  } 次，正确率 ${formatAccuracy(totals.value.accuracy, totals.value.practiceCount)}`
})

function barHeight(count: number): string {
  if (count <= 0 || maxCount.value <= 0) return '2px'
  return `${Math.max(6, Math.round((count / maxCount.value) * 100))}%`
}

function correctSegmentHeight(point: StatsTrendPoint): string {
  if (point.practice_count <= 0) return '0%'
  const ratio = Math.min(1, Math.max(0, point.correct_count / point.practice_count))
  return `${Math.round(ratio * 100)}%`
}
</script>

<template>
  <figure class="trend">
    <div class="trend__top">
      <p class="trend__summary">
        共 <strong>{{ totals.practiceCount }}</strong> 次练习
        <span class="trend__sep" aria-hidden="true">·</span>
        答对 <strong>{{ totals.correctCount }}</strong> 次
        <span class="trend__sep" aria-hidden="true">·</span>
        正确率 {{ formatAccuracy(totals.accuracy, totals.practiceCount) }}
      </p>

      <div class="trend__legend" aria-hidden="true">
        <span>
          <i class="trend__swatch trend__swatch--total"></i>
          练习
        </span>
        <span>
          <i class="trend__swatch trend__swatch--correct"></i>
          答对
        </span>
      </div>
    </div>

    <div v-if="hasData" class="trend__plot" role="img" :aria-label="chartLabel">
      <ol class="trend__bars">
        <li
          v-for="point in points"
          :key="point.date"
          class="trend__col"
          :title="`${point.date}：练习 ${point.practice_count} 次，答对 ${point.correct_count} 次`"
        >
          <span class="trend__count" :class="{ 'trend__count--zero': point.practice_count === 0 }">
            {{ point.practice_count }}
          </span>
          <div class="trend__track">
            <div class="trend__bar" :style="{ height: barHeight(point.practice_count) }">
              <span
                class="trend__bar-correct"
                :style="{ height: correctSegmentHeight(point) }"
              ></span>
            </div>
          </div>
        </li>
      </ol>
    </div>

    <div v-else class="trend__empty">
      <p>近 7 天还没有练习记录</p>
      <span>完成一次练习后，这里会显示每天的练习量与答对数量。</span>
    </div>

    <ol class="trend__dates" aria-label="统计日期">
      <li v-for="point in points" :key="point.date">
        <time :datetime="point.date" :aria-label="point.date">
          <span class="trend__date-full" aria-hidden="true">
            {{ formatTrendDay(point.date) }}
          </span>
          <span class="trend__date-short" aria-hidden="true">
            {{ formatTrendDayShort(point.date) }}
          </span>
        </time>
      </li>
    </ol>

    <table class="sr-only">
      <caption>
        近 7 天每日练习记录
      </caption>
      <thead>
        <tr>
          <th scope="col">日期</th>
          <th scope="col">练习次数</th>
          <th scope="col">答对次数</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="point in points" :key="point.date">
          <th scope="row">{{ point.date }}</th>
          <td>{{ point.practice_count }}</td>
          <td>{{ point.correct_count }}</td>
        </tr>
      </tbody>
    </table>
  </figure>
</template>

<style scoped>
.trend {
  display: flex;
  flex-direction: column;
}

.trend__top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2) var(--space-4);
  margin-bottom: var(--space-4);
}

.trend__summary {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.trend__summary strong {
  color: var(--color-text-1);
  font-family: var(--font-mono);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.trend__sep {
  margin: 0 3px;
  color: var(--color-border-strong);
}

.trend__legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.trend__legend span {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.trend__swatch {
  width: 10px;
  height: 10px;
  flex: none;
  border-radius: var(--radius-sm);
}

.trend__swatch--total {
  border: 1px solid var(--color-primary-border);
  background: var(--color-primary-soft);
}

.trend__swatch--correct {
  background: var(--color-primary);
}

.trend__plot {
  padding-top: var(--space-1);
}

.trend__bars,
.trend__dates {
  display: flex;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.trend__bars > li,
.trend__dates > li {
  flex: 1 1 0;
  min-width: 0;
}

.trend__col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
}

.trend__count {
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 20px;
  font-variant-numeric: tabular-nums;
}

.trend__count--zero {
  color: var(--color-text-3);
}

.trend__track {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  width: 100%;
  height: 112px;
}

.trend__bar {
  display: flex;
  align-items: flex-end;
  width: min(30px, 72%);
  min-height: 2px;
  overflow: hidden;
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  background: var(--color-primary-soft);
}

.trend__bar-correct {
  display: block;
  width: 100%;
  background: var(--color-primary);
}

.trend__dates {
  margin-top: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
}

.trend__dates > li {
  text-align: center;
}

.trend__dates time {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-variant-numeric: tabular-nums;
}

.trend__date-short {
  display: none;
}

.trend__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  min-height: 146px;
  padding: var(--space-5) var(--space-4);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
  text-align: center;
}

.trend__empty p {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 600;
}

.trend__empty span {
  max-width: 40ch;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

@media (max-width: 600px) {
  .trend__top {
    align-items: flex-start;
    flex-direction: column;
    margin-bottom: var(--space-3);
  }

  .trend__date-full {
    display: none;
  }

  .trend__date-short {
    display: inline;
  }

  .trend__track {
    height: 96px;
  }

  .trend__bar {
    width: min(24px, 78%);
  }
}
</style>
