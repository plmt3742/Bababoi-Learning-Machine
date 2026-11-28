<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { RouterLink } from 'vue-router'

import AdminPageHeader from '../components/AdminPageHeader.vue'
import AppIcon from '../components/AppIcon.vue'
import MetricCard from '../components/MetricCard.vue'
import TrendChart from '../components/TrendChart.vue'
import { useAdminData } from '../stores/adminData'

const data = useAdminData()

const trendMode = ref<'success' | 'latency'>('success')
const refreshing = ref(false)

const overview = computed(() => data.overview)
const stats = computed(() => overview.value?.stats ?? null)
const failedTasks = computed(() => overview.value?.failed_tasks ?? [])
const pendingRequests = computed(() => overview.value?.pending_password_requests ?? [])
const recentAudit = computed(() => (overview.value?.recent_audit ?? []).slice(0, 4))
const activeAlerts = computed(() => (overview.value?.alerts ?? []).filter((alert) => alert.status === 'active'))
const primaryAlert = computed(() => activeAlerts.value[0] ?? null)
const generatedAt = computed(() => overview.value?.generated_at ?? '—')

const trendPoints = computed(() =>
  trendMode.value === 'success' ? overview.value?.trend.success ?? [] : overview.value?.trend.latency ?? [],
)
const trendValue = computed(() => {
  const latest = trendPoints.value.at(-1)
  if (!latest) return '—'
  return `${latest.value.toFixed(1)}${trendMode.value === 'success' ? '%' : 's'}`
})

const queue = computed(() => ({
  done: stats.value?.tasks.done_24h ?? 0,
  running: stats.value?.tasks.running ?? 0,
  queued: stats.value?.tasks.queued ?? 0,
  failed: stats.value?.tasks.failed ?? 0,
}))
const queueTotal = computed(() => Object.values(queue.value).reduce((sum, value) => sum + value, 0))
const queueWidth = (value: number): string =>
  `${(value / Math.max(queueTotal.value, 1)) * 100}%`

const attentionText = computed(() => {
  const failed = stats.value?.tasks.failed ?? 0
  const pending = stats.value?.password_requests.pending ?? 0
  const alerts = activeAlerts.value.length
  if (!failed && !pending && !alerts) return ''
  return `${failed} 个失败任务 · ${pending} 个密码申请待审批 · ${alerts} 条活跃告警`
})

const aiCost = computed(() => {
  const cost = stats.value?.ai.estimated_cost
  return cost === null || cost === undefined ? '—' : `¥${cost.toFixed(2)}`
})

function seconds(value: number): string {
  return `${(value / 1000).toFixed(1)}s`
}

function formatTokens(value: number): string {
  return new Intl.NumberFormat('zh-CN').format(value)
}

async function refresh(): Promise<void> {
  if (refreshing.value) return
  refreshing.value = true
  try {
    await data.loadOverview()
  } catch (cause) {
    Message.error(cause instanceof Error ? cause.message : '总览加载失败')
  } finally {
    refreshing.value = false
  }
}

onMounted(() => {
  if (!data.overview) void refresh()
})
</script>

<template>
  <div class="adm-page">
    <AdminPageHeader
      eyebrow="监控 · 运营总览"
      title="运营总览"
      description="系统、AI 与学习数据的同一张桌面。先看异常，再决定要不要动手。"
    >
      <template #actions>
        <button class="adm-btn adm-btn--outline" type="button" :disabled="refreshing" @click="refresh">
          <AppIcon name="refresh" :size="15" />
          {{ refreshing ? '刷新中…' : '刷新' }}
        </button>
      </template>
    </AdminPageHeader>

    <div v-if="attentionText" class="adm-alert-strip">
      <AppIcon name="warning" :size="15" />
      <span>{{ attentionText }}</span>
      <div class="adm-alert-strip__actions">
        <RouterLink class="adm-btn adm-btn--quiet adm-btn--sm" to="/tasks">查看任务</RouterLink>
        <RouterLink class="adm-btn adm-btn--quiet adm-btn--sm" to="/password-requests">去审批</RouterLink>
        <RouterLink
          v-if="primaryAlert?.target"
          class="adm-btn adm-btn--quiet adm-btn--sm"
          :to="primaryAlert.target.to"
        >
          {{ primaryAlert.target.label }}
        </RouterLink>
        <RouterLink v-else class="adm-btn adm-btn--quiet adm-btn--sm" to="/alerts">告警中心</RouterLink>
      </div>
    </div>

    <section class="adm-kpi-grid" aria-label="关键指标">
      <MetricCard
        label="用户总数"
        :value="String(stats?.users.total ?? '—')"
        :hint="stats ? `活跃 ${stats.users.active} · 禁用 ${stats.users.disabled}` : '加载中'"
        icon="users"
      />
      <MetricCard
        label="错题总数"
        :value="String(stats?.content.questions ?? '—')"
        :hint="stats ? `已隐藏 ${stats.content.hidden} · 已标记 ${stats.content.flagged}` : '加载中'"
        icon="file"
      />
      <MetricCard
        label="生成题"
        :value="String(stats?.content.generated ?? '—')"
        hint="AI 生成并入库"
        icon="spark"
      />
      <MetricCard
        label="练习记录"
        :value="String(stats?.content.practice ?? '—')"
        hint="累计练习次数"
        icon="tasks"
      />
      <MetricCard
        label="AI 成功率"
        :value="stats ? stats.ai.success_rate.toFixed(1) : '—'"
        :unit="stats ? '%' : ''"
        :hint="stats ? `24h 调用 ${stats.ai.calls_24h} 次` : '加载中'"
        icon="spark"
      />
      <MetricCard
        label="P95 延迟"
        :value="stats ? seconds(stats.ai.p95_latency_ms) : '—'"
        :hint="stats ? `P50 ${seconds(stats.ai.p50_latency_ms)}` : '加载中'"
        icon="clock"
      />
      <MetricCard
        label="失败任务"
        :value="String(stats?.tasks.failed ?? '—')"
        :hint="stats ? `${stats.tasks.queued} 排队 · ${stats.tasks.running} 生成中` : '加载中'"
        danger
        icon="alert"
      />
      <MetricCard
        label="估算成本"
        :value="aiCost"
        :hint="stats ? `${formatTokens(stats.ai.input_tokens + stats.ai.output_tokens)} tokens` : '加载中'"
        icon="system"
      />
    </section>

    <div class="adm-split">
      <section class="adm-panel">
        <div class="adm-panel__head">
          <h2>AI 质量趋势</h2>
          <span class="adm-muted">更新于 {{ generatedAt }}</span>
        </div>
        <div class="adm-panel__body">
          <div class="adm-chart-card__head">
            <div>
              <p class="adm-muted">{{ trendMode === 'success' ? '近 7 天调用成功率' : '近 7 天 P95 延迟' }}</p>
              <div class="adm-chart-summary">
                <strong>{{ trendValue }}</strong>
                <span>{{ trendMode === 'success' ? '当前窗口' : '越低越好' }}</span>
              </div>
            </div>
            <div class="adm-chart-card__legend">
              <div class="adm-seg">
                <button type="button" :class="{ 'is-active': trendMode === 'success' }" @click="trendMode = 'success'">成功率</button>
                <button type="button" :class="{ 'is-active': trendMode === 'latency' }" @click="trendMode = 'latency'">延迟</button>
              </div>
            </div>
          </div>
          <TrendChart
            v-if="trendPoints.length"
            :points="trendPoints"
            :tone="trendMode === 'success' ? 'blue' : 'amber'"
            :suffix="trendMode === 'success' ? '%' : 's'"
            :digits="1"
          />
          <div v-else class="adm-empty">
            <strong>暂无趋势数据</strong>
            <p>接口返回的 trend 为空，通常表示数据库还没有足够的调用记录。</p>
          </div>
        </div>
      </section>

      <section class="adm-panel">
        <div class="adm-panel__head">
          <h2>任务队列</h2>
          <span class="adm-muted">最近 24h</span>
        </div>
        <div class="adm-panel__body">
          <div class="adm-chart-summary">
            <strong>{{ queueTotal }}</strong>
            <span>个任务进入队列</span>
          </div>
          <div class="adm-queue-bar" aria-label="任务队列状态">
            <span class="adm-queue-bar__done" :style="{ width: queueWidth(queue.done) }" />
            <span class="adm-queue-bar__running" :style="{ width: queueWidth(queue.running) }" />
            <span class="adm-queue-bar__queued" :style="{ width: queueWidth(queue.queued) }" />
            <span class="adm-queue-bar__failed" :style="{ width: queueWidth(queue.failed) }" />
          </div>
          <div class="adm-queue-legend">
            <div><i class="adm-queue-bar__done" />完成 <strong>{{ queue.done }}</strong></div>
            <div><i class="adm-queue-bar__running" />生成中 <strong>{{ queue.running }}</strong></div>
            <div><i class="adm-queue-bar__queued" />排队中 <strong>{{ queue.queued }}</strong></div>
            <div><i class="adm-queue-bar__failed" />失败 <strong>{{ queue.failed }}</strong></div>
          </div>
          <div class="adm-queue-foot">
            <span>最老排队 <span class="adm-mono">{{ stats ? `${stats.tasks.oldest_queue_seconds}s` : '—' }}</span></span>
            <RouterLink class="adm-link" to="/tasks">查看队列 →</RouterLink>
          </div>
        </div>
      </section>
    </div>

    <div class="adm-split">
      <section class="adm-panel">
        <div class="adm-panel__head">
          <h2>最近失败任务</h2>
          <RouterLink class="adm-link" to="/tasks">查看全部 {{ failedTasks.length }} 条</RouterLink>
        </div>
        <div class="adm-table-wrap">
          <table class="adm-table">
            <thead>
              <tr>
                <th>任务 / 题目</th>
                <th>阶段</th>
                <th>错误</th>
                <th>时间</th>
                <th />
              </tr>
            </thead>
            <tbody>
              <tr v-for="task in failedTasks" :key="task.id">
                <td>
                  <div class="adm-table__primary">{{ task.question }}</div>
                  <div class="adm-table__sub">{{ task.code }} · {{ task.username }}</div>
                </td>
                <td>{{ task.stage === 'analysis' ? '分析' : `生题 · 第 ${task.targetIndex ?? 1} 段` }}</td>
                <td><span class="adm-tag adm-tag--danger">{{ task.errorCode ?? '—' }}</span></td>
                <td class="adm-mono">{{ task.createdAt }}</td>
                <td class="adm-table__right"><RouterLink class="adm-link" to="/tasks">详情</RouterLink></td>
              </tr>
              <tr v-if="!failedTasks.length">
                <td colspan="5"><div class="adm-empty"><strong>暂无失败任务</strong><p>后端返回的 failed_tasks 为空。</p></div></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <div class="adm-stack">
        <section class="adm-panel">
          <div class="adm-panel__head">
            <h2>待审批密码申请</h2>
            <span class="adm-muted">{{ pendingRequests.length }} 待处理</span>
          </div>
          <div class="adm-todo-list">
            <div v-for="request in pendingRequests" :key="request.id" class="adm-todo">
              <span class="adm-todo__icon adm-todo__icon--amber"><AppIcon name="key" :size="15" /></span>
              <div class="adm-todo__copy">
                <strong>{{ request.username }}</strong>
                <span>{{ request.reason }}</span>
              </div>
              <RouterLink class="adm-btn adm-btn--quiet adm-btn--sm" to="/password-requests">审批</RouterLink>
            </div>
            <div v-if="!pendingRequests.length" class="adm-empty">
              <strong>没有待审批申请</strong>
              <p>学生提交密码申请后会出现在这里。</p>
            </div>
          </div>
        </section>

        <section class="adm-panel">
          <div class="adm-panel__head">
            <h2>最近操作</h2>
            <RouterLink class="adm-link" to="/audit">审计日志 →</RouterLink>
          </div>
          <ul class="adm-timeline">
            <li v-for="entry in recentAudit" :key="entry.id">
              <span class="adm-timeline__dot" />
              <p class="adm-timeline__title">{{ entry.action }} · {{ entry.target }}</p>
              <p class="adm-timeline__meta"><time>{{ entry.time }}</time><span>{{ entry.admin }}</span></p>
            </li>
            <li v-if="!recentAudit.length">
              <span class="adm-timeline__dot" />
              <p class="adm-timeline__title">暂无审计记录</p>
              <p class="adm-timeline__meta"><span>—</span></p>
            </li>
          </ul>
        </section>
      </div>
    </div>
  </div>
</template>
