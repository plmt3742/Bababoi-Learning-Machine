<script setup lang="ts">
import { computed } from 'vue'
import { IconRefresh } from '@arco-design/web-vue/es/icon'
import ErrorState from '../components/common/ErrorState.vue'
import PageHeader from '../components/common/PageHeader.vue'
import HomeDashboardSkeleton from '../components/home/HomeDashboardSkeleton.vue'
import HomeRecentQuestions from '../components/home/HomeRecentQuestions.vue'
import HomeStatusStrip from '../components/home/HomeStatusStrip.vue'
import HomeTasks from '../components/home/HomeTasks.vue'
import HomeWeakPoints from '../components/home/HomeWeakPoints.vue'
import StatsStatCard from '../components/stats/StatsStatCard.vue'
import { useHomeOverview } from '../composables/useHomeOverview'
import { formatStatsTime } from '../utils/stats'
import { buildHomeKpis, draftSummary, formatHomeDate, sectionErrorText } from '../utils/home'

const {
  stats,
  questions,
  questionTotal,
  practiceTotal,
  draft,
  errors,
  loading,
  refreshing,
  activeTasks,
  failedTasks,
  attentionTasks,
  weakPoints,
  lastUpdatedText,
  allFailed,
  refresh,
} = useHomeOverview()

const description = `${formatHomeDate(new Date())} · 继续你的错题闭环。`

const kpis = computed(() => buildHomeKpis(stats.value, questionTotal.value, practiceTotal.value))
const draftText = computed(() => draftSummary(draft.value))
const hasDerivedData = computed(() => questionTotal.value !== null || practiceTotal.value !== null)

const activeCount = computed(() => (errors.value.tasks ? null : activeTasks.value.length))
const failedCount = computed(() => (errors.value.tasks ? null : failedTasks.value.length))
const draftState = computed<'present' | 'none' | 'unknown'>(() => {
  if (errors.value.draft) return 'unknown'
  return draft.value ? 'present' : 'none'
})

const statsErrorText = computed(() => sectionErrorText(errors.value.stats))
const questionErrorText = computed(() => sectionErrorText(errors.value.questions))
const taskErrorText = computed(() => sectionErrorText(errors.value.tasks))
const draftErrorText = computed(() => sectionErrorText(errors.value.draft))

const statsNote = computed(() => {
  if (!statsErrorText.value) return ''
  if (stats.value) return '统计刷新失败，正在显示上次数据。'
  if (hasDerivedData.value) return '统计概览暂不可用，已展示可推导的数据。'
  return '统计概览暂不可用。'
})

const firstError = computed(() => {
  const order = ['stats', 'questions', 'tasks', 'draft'] as const
  for (const section of order) {
    const error = errors.value[section]
    if (error) return error
  }
  return null
})

const firstErrorMessage = computed(
  () => firstError.value?.message ?? '请求没有成功，请检查网络后重试。',
)
const firstErrorCode = computed(() => firstError.value?.code ?? '')

function handleRefresh(): void {
  void refresh()
}
</script>

<template>
  <div class="home">
    <PageHeader eyebrow="Overview" title="学习概览" :description="description">
      <template #actions>
        <button
          class="btn btn--outline home-refresh"
          type="button"
          :disabled="loading || refreshing"
          :aria-busy="refreshing"
          @click="handleRefresh"
        >
          <IconRefresh aria-hidden="true" />
          {{ refreshing ? '刷新中…' : '刷新' }}
        </button>
      </template>
    </PageHeader>

    <HomeDashboardSkeleton v-if="loading" />

    <template v-else>
      <ErrorState
        v-if="allFailed"
        title="学习概览加载失败"
        :message="firstErrorMessage"
        :code="firstErrorCode"
        @retry="handleRefresh"
      />

      <template v-else>
        <HomeStatusStrip
          :active-count="activeCount"
          :failed-count="failedCount"
          :draft-state="draftState"
        />

        <RouterLink v-if="draft" class="draft-bar" to="/questions/new">
          <span class="tag tag--draft">草稿</span>
          <span class="draft-bar__body">
            <span class="draft-bar__title">未完成草稿 · 继续编辑</span>
            <span class="draft-bar__excerpt">{{ draftText }}</span>
          </span>
          <span class="draft-bar__meta">
            <time class="draft-bar__time" :datetime="draft.updated_at">
              {{ formatStatsTime(draft.updated_at) }}
            </time>
            <span class="draft-bar__go">
              继续编辑
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path d="m9 6 6 6-6 6" />
              </svg>
            </span>
          </span>
        </RouterLink>

        <div v-else-if="draftErrorText" class="draft-warning" role="status">
          <span>草稿状态暂不可用：{{ draftErrorText }}</span>
          <button class="btn btn--quiet btn--sm" type="button" @click="handleRefresh">重试</button>
        </div>

        <section class="kpi-grid" aria-label="学习数据概览">
          <h2 class="sr-only">学习数据概览</h2>
          <StatsStatCard
            v-for="kpi in kpis"
            :key="kpi.label"
            :label="kpi.label"
            :value="kpi.value"
            :hint="kpi.hint"
          />
        </section>

        <div class="kpi-meta">
          <p v-if="statsErrorText" class="kpi-note" role="status">
            <span>{{ statsNote }}</span>
            <button class="btn btn--quiet btn--sm" type="button" @click="handleRefresh">
              重试
            </button>
          </p>
          <p v-else-if="stats" class="kpi-updated">
            统计更新于
            <time :datetime="stats.updated_at">{{ lastUpdatedText }}</time>
          </p>
        </div>

        <div class="home-grid">
          <HomeRecentQuestions
            :questions="questions"
            :error-text="questionErrorText"
            @retry="handleRefresh"
          />

          <div class="home-grid__side">
            <HomeWeakPoints
              :points="weakPoints"
              :error-text="statsErrorText"
              @retry="handleRefresh"
            />
            <HomeTasks :tasks="attentionTasks" :error-text="taskErrorText" @retry="handleRefresh" />
          </div>
        </div>
      </template>

      <nav class="quick-bar" aria-label="快捷操作">
        <p class="quick-bar__label">快速开始</p>
        <div class="quick-bar__actions">
          <RouterLink class="btn btn--primary" to="/questions/new">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              aria-hidden="true"
            >
              <path d="M12 5v14M5 12h14" />
            </svg>
            录入错题
          </RouterLink>
          <RouterLink class="btn btn--outline" to="/questions">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.7"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M5 4h9l5 5v11H5z" />
              <path d="M14 4v5h5" />
              <path d="M8 13h8M8 16h6" />
            </svg>
            错题本
          </RouterLink>
          <RouterLink class="btn btn--outline" to="/practice">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.7"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="9" />
              <path d="m10 8 6 4-6 4z" />
            </svg>
            练习
          </RouterLink>
          <RouterLink class="btn btn--outline" to="/stats">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              aria-hidden="true"
            >
              <path d="M4 20h16" />
              <path d="M6 20v-6M12 20V8M18 20v-9" />
            </svg>
            统计
          </RouterLink>
        </div>
      </nav>
    </template>
  </div>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.home-refresh:disabled :deep(svg) {
  animation: home-refresh-spin 0.9s linear infinite;
}

@keyframes home-refresh-spin {
  to {
    transform: rotate(360deg);
  }
}

.draft-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  color: inherit;
  transition: border-color 0.15s ease;
}

.draft-bar:hover {
  border-color: var(--color-border-strong);
  color: inherit;
}

.draft-bar__body {
  display: flex;
  flex: 1 1 280px;
  flex-direction: column;
  min-width: 0;
}

.draft-bar__title {
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 600;
}

.draft-bar__excerpt {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  overflow-wrap: anywhere;
}

.draft-bar__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-left: auto;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.draft-bar__time {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

.draft-bar__go {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--color-primary-active);
  font-weight: 500;
}

.draft-bar:hover .draft-bar__go {
  color: var(--color-primary);
}

.draft-bar__go svg {
  width: 15px;
  height: 15px;
}

.draft-warning {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-warning-border);
  border-radius: var(--radius-md);
  background: var(--color-warning-soft);
  color: var(--color-warning-text);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
}

.kpi-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
  min-height: 20px;
  margin-top: calc(-1 * var(--space-1));
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: 20px;
}

.kpi-note {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-1);
  color: var(--color-warning-text);
}

.kpi-note .btn {
  flex: none;
}

.kpi-updated {
  margin-left: auto;
}

.kpi-updated time {
  font-family: var(--font-mono);
}

.home-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
  align-items: start;
  gap: var(--space-4);
}

.home-grid__side {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-width: 0;
}

.quick-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-3);
  margin-top: var(--space-1);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.quick-bar__label {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 500;
}

.quick-bar__actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-left: auto;
}

@media (max-width: 1023px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .home-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .home {
    gap: var(--space-3);
  }

  .draft-bar {
    align-items: flex-start;
  }

  .draft-bar__body {
    flex-basis: 100%;
  }

  .draft-bar__meta {
    width: 100%;
    justify-content: space-between;
    margin-left: 0;
  }

  .kpi-grid,
  .home-grid {
    gap: var(--space-3);
  }

  .kpi-meta {
    margin-top: 0;
  }

  .home-grid__side {
    gap: var(--space-3);
  }

  .quick-bar {
    align-items: stretch;
    flex-direction: column;
  }

  .quick-bar__actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    width: 100%;
    margin-left: 0;
  }

  .quick-bar__actions .btn {
    width: 100%;
  }
}
</style>
