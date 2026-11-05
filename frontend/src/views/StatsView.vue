<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { IconRefresh } from '@arco-design/web-vue/es/icon'
import PageHeader from '../components/common/PageHeader.vue'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import MasteryBar from '../components/stats/MasteryBar.vue'
import StatsSkeleton from '../components/stats/StatsSkeleton.vue'
import StatsStatCard from '../components/stats/StatsStatCard.vue'
import TrendChart from '../components/stats/TrendChart.vue'
import WeakPointList from '../components/stats/WeakPointList.vue'
import { getStatsOverview } from '../api/stats'
import { normalizeApiError } from '../api/errors'
import type { StatsOverview } from '../api/types'
import { formatAccuracy, formatStatsTime, formatTrendDay, summarizeTrend } from '../utils/stats'

const router = useRouter()

const overview = ref<StatsOverview | null>(null)
const loading = ref(true)
const refreshing = ref(false)
const errorMessage = ref('')
const errorCode = ref('')

let requestToken = 0

const week = computed(() => summarizeTrend(overview.value?.recent_trend ?? []))

const hasAnyData = computed(() => {
  const stats = overview.value
  if (!stats) return false

  return (
    stats.total_questions > 0 ||
    stats.total_generated_questions > 0 ||
    stats.total_practice_records > 0
  )
})

const accuracyText = computed(() =>
  overview.value
    ? formatAccuracy(overview.value.accuracy, overview.value.total_practice_records)
    : '—',
)

const accuracyHint = computed(() =>
  overview.value && overview.value.total_practice_records > 0
    ? `累计 ${overview.value.total_practice_records} 次练习`
    : '完成练习后开始统计',
)

const trendRange = computed(() => {
  const points = overview.value?.recent_trend ?? []
  if (points.length === 0) return ''

  return `${formatTrendDay(points[0].date)} — ${formatTrendDay(points[points.length - 1].date)}`
})

const updatedText = computed(() =>
  overview.value ? formatStatsTime(overview.value.updated_at) : '',
)

async function loadStats(mode: 'initial' | 'refresh'): Promise<void> {
  const token = ++requestToken
  errorMessage.value = ''
  errorCode.value = ''

  if (mode === 'initial') loading.value = true
  else refreshing.value = true

  try {
    const result = await getStatsOverview()
    if (token !== requestToken) return
    overview.value = result
  } catch (cause) {
    if (token !== requestToken) return

    const apiError = normalizeApiError(cause)
    errorMessage.value = apiError.message
    errorCode.value = apiError.code
  } finally {
    if (token === requestToken) {
      loading.value = false
      refreshing.value = false
    }
  }
}

function handleRefresh(): void {
  if (refreshing.value || loading.value) return
  void loadStats('refresh')
}

function retry(): void {
  void loadStats('initial')
}

function goCreate(): void {
  void router.push('/questions/new')
}

onMounted(() => {
  void loadStats('initial')
})

onBeforeUnmount(() => {
  requestToken += 1
})
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="Stats"
      title="学习概览"
      description="看清错题规模、练习正确率与薄弱知识点，把复习精力放在最需要的地方。"
    >
      <template #actions>
        <button
          class="btn btn--outline stats-refresh"
          type="button"
          :disabled="refreshing || loading"
          :aria-busy="refreshing"
          @click="handleRefresh"
        >
          <IconRefresh aria-hidden="true" />
          {{ refreshing ? '刷新中…' : '刷新' }}
        </button>
      </template>
    </PageHeader>

    <div v-if="errorMessage && overview" class="stats-alert" role="alert">
      <span>
        统计刷新失败：{{ errorMessage }}
        <code v-if="errorCode" class="stats-alert__code">（{{ errorCode }}）</code>
      </span>
      <button class="btn btn--danger btn--sm" type="button" @click="handleRefresh">重试</button>
    </div>

    <StatsSkeleton v-if="loading" />

    <ErrorState
      v-else-if="errorMessage && !overview"
      title="统计数据加载失败"
      :message="errorMessage"
      :code="errorCode"
      @retry="retry"
    />

    <EmptyState
      v-else-if="!hasAnyData"
      title="还没有学习数据"
      description="录入第一道错题并完成练习后，这里会展示错题规模、正确率、薄弱知识点与近 7 天趋势。"
      action-label="去录入错题"
      @action="goCreate"
    />

    <template v-else-if="overview">
      <section class="kpi-grid" aria-label="学习数据概览">
        <StatsStatCard
          label="错题总数"
          :value="String(overview.total_questions)"
          :hint="`相似题 ${overview.total_generated_questions} 道`"
        />
        <StatsStatCard
          label="练习次数"
          :value="String(overview.total_practice_records)"
          :hint="`近 7 天 ${week.practiceCount} 次`"
        />
        <StatsStatCard label="正确率" :value="accuracyText" :hint="accuracyHint" />
        <StatsStatCard
          label="已掌握题数"
          :value="String(overview.mastered_count)"
          :hint="`复习 ${overview.reviewing_count} · 未掌握 ${overview.unmastered_count}`"
        />
      </section>

      <div class="stats-panels">
        <section class="panel">
          <header class="panel__head">
            <h2>薄弱知识点</h2>
            <span class="panel__head-hint">按错误次数排序 · Top 5</span>
          </header>
          <div class="panel__body panel__body--flush">
            <WeakPointList :points="overview.weak_knowledge_points" />
          </div>
        </section>

        <section class="panel">
          <header class="panel__head">
            <h2>掌握度分布</h2>
            <span class="panel__head-hint">共 {{ overview.total_questions }} 道错题</span>
          </header>
          <div class="panel__body">
            <MasteryBar
              :mastered="overview.mastered_count"
              :reviewing="overview.reviewing_count"
              :unmastered="overview.unmastered_count"
            />
          </div>
        </section>
      </div>

      <section class="panel">
        <header class="panel__head">
          <h2>近 7 天练习趋势</h2>
          <span class="panel__head-hint">{{ trendRange }}</span>
        </header>
        <div class="panel__body">
          <TrendChart :points="overview.recent_trend" />
        </div>
      </section>

      <footer class="stats-foot">
        <p>正确率按全部练习记录计算；薄弱知识点按错误次数排序，至少包含 1 次练习。</p>
        <p v-if="updatedText" class="stats-foot__updated">
          更新于
          <time :datetime="overview.updated_at">{{ updatedText }}</time>
        </p>
      </footer>
    </template>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.stats-refresh:disabled :deep(svg) {
  animation: stats-refresh-spin 0.9s linear infinite;
}

@keyframes stats-refresh-spin {
  to {
    transform: rotate(360deg);
  }
}

.stats-alert {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-danger-border);
  border-radius: var(--radius-md);
  background: var(--color-danger-soft);
  color: var(--color-danger-text);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.stats-alert__code {
  margin-left: 2px;
  color: var(--color-danger-text);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
}

.stats-panels {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
  align-items: start;
  gap: var(--space-4);
}

.stats-panels > .panel > .panel__body--flush {
  padding: 0;
}

.stats-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-1) var(--space-4);
  padding-top: var(--space-1);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.stats-foot p {
  text-wrap: pretty;
}

.stats-foot time {
  font-family: var(--font-mono);
}

@media (max-width: 1023px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stats-panels {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .page {
    gap: var(--space-3);
  }

  .kpi-grid,
  .stats-panels {
    gap: var(--space-3);
  }
}
</style>
