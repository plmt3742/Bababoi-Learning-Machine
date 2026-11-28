<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { RouterLink } from 'vue-router'

import AdminPageHeader from '../components/AdminPageHeader.vue'
import AppIcon from '../components/AppIcon.vue'
import MetricCard from '../components/MetricCard.vue'
import StatusTag from '../components/StatusTag.vue'
import { useAdminData } from '../stores/adminData'
import type { AdminTask, AdminTaskDetail } from '../types'

type StatusFilter = 'all' | AdminTask['status']

const data = useAdminData()

const keyword = ref('')
const status = ref<StatusFilter>('all')
const drawerVisible = ref(false)
const detail = ref<AdminTaskDetail | null>(null)
const detailLoading = ref(false)
const busyTaskId = ref<number | null>(null)

let filterTimer: number | undefined

const taskStats = computed(() => data.overview?.stats.tasks ?? null)

const filteredTasks = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  return data.tasks.filter((task) => {
    if (status.value !== 'all' && task.status !== status.value) return false
    if (!query) return true
    return `${task.code} ${task.question} ${task.username} ${task.errorCode ?? ''}`
      .toLowerCase()
      .includes(query)
  })
})

function errorText(cause: unknown): string {
  return cause instanceof Error ? cause.message : '操作失败，请稍后重试'
}

async function load(): Promise<void> {
  try {
    await data.loadTasks({
      q: keyword.value.trim() || undefined,
      status: status.value === 'all' ? 'all' : status.value,
    })
  } catch (cause) {
    Message.error(errorText(cause))
  }
}

function scheduleLoad(): void {
  if (filterTimer) window.clearTimeout(filterTimer)
  filterTimer = window.setTimeout(() => {
    void load()
  }, 280)
}

watch([keyword, status], scheduleLoad)
onMounted(load)
onUnmounted(() => {
  if (filterTimer) window.clearTimeout(filterTimer)
})

function statusTone(task: AdminTask): 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'running' {
  if (task.status === 'done') return 'success'
  if (task.status === 'failed') return 'danger'
  if (task.status === 'running') return 'running'
  if (task.status === 'queued') return 'info'
  return 'neutral'
}

function statusLabel(task: AdminTask): string {
  return {
    queued: '排队中',
    running: '生成中',
    done: '完成',
    failed: '失败',
    canceled: '已取消',
  }[task.status]
}

function stageLabel(task: AdminTask): string {
  if (task.stage === 'analysis') return '分析'
  return `生题 · 第 ${task.targetIndex ?? 1} 段`
}

async function openTask(task: AdminTask): Promise<void> {
  drawerVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await data.loadTaskDetail(task.id)
  } catch (cause) {
    Message.error(errorText(cause))
    drawerVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

async function retryTask(task: AdminTask): Promise<void> {
  if (busyTaskId.value !== null) return
  busyTaskId.value = task.id
  try {
    await data.retryTask(task.id)
    Message.success(`已重新提交 ${task.code}`)
    if (detail.value?.id === task.id) {
      detail.value = await data.loadTaskDetail(task.id)
    }
  } catch (cause) {
    Message.error(errorText(cause))
  } finally {
    busyTaskId.value = null
  }
}

async function cancelTask(task: AdminTask): Promise<void> {
  if (busyTaskId.value !== null) return
  busyTaskId.value = task.id
  try {
    await data.cancelTask(task.id)
    Message.success(`已取消 ${task.code} 的排队`)
    if (detail.value?.id === task.id) {
      detail.value = await data.loadTaskDetail(task.id)
    }
  } catch (cause) {
    Message.error(errorText(cause))
  } finally {
    busyTaskId.value = null
  }
}

async function refresh(): Promise<void> {
  try {
    await Promise.all([data.loadTasks(), data.loadOverview()])
    Message.success('任务队列已刷新')
  } catch (cause) {
    Message.error(errorText(cause))
  }
}
</script>

<template>
  <div class="adm-page">
    <AdminPageHeader
      eyebrow="AI 运维 · 任务"
      title="任务中心"
      description="查看分析/生题任务的队列与错误；失败可重试，排队中可取消，running 不强行中断。"
    >
      <template #actions>
        <button class="adm-btn adm-btn--outline" type="button" @click="refresh">
          <AppIcon name="refresh" :size="15" />
          刷新
        </button>
      </template>
    </AdminPageHeader>

    <section class="adm-kpi-grid" aria-label="队列概览">
      <MetricCard
        label="排队中"
        :value="String(taskStats?.queued ?? '—')"
        :hint="taskStats ? `最老等待 ${taskStats.oldest_queue_seconds}s` : '加载中'"
        icon="tasks"
      />
      <MetricCard
        label="生成中"
        :value="String(taskStats?.running ?? '—')"
        hint="由后端 worker 执行"
        icon="spark"
      />
      <MetricCard
        label="失败"
        :value="String(taskStats?.failed ?? '—')"
        hint="最多重试 3 次"
        :trend="(taskStats?.failed ?? 0) > 0 ? '需处理' : '正常'"
        :trend-tone="(taskStats?.failed ?? 0) > 0 ? 'negative' : 'neutral'"
        :danger="(taskStats?.failed ?? 0) > 0"
        icon="alert"
      />
      <MetricCard
        label="今日完成"
        :value="String(taskStats?.done_24h ?? '—')"
        :hint="taskStats ? `已取消 ${taskStats.canceled_24h}` : '加载中'"
        icon="check"
      />
    </section>

    <section class="adm-panel">
      <div class="adm-toolbar">
        <a-input v-model="keyword" class="adm-search" placeholder="搜索任务号、题干、用户或错误码" allow-clear>
          <template #prefix><AppIcon name="search" :size="14" /></template>
        </a-input>
        <a-select v-model="status" class="adm-filter" aria-label="任务状态筛选">
          <a-option value="all">全部状态</a-option>
          <a-option value="queued">排队中</a-option>
          <a-option value="running">生成中</a-option>
          <a-option value="failed">失败</a-option>
          <a-option value="done">完成</a-option>
          <a-option value="canceled">已取消</a-option>
        </a-select>
        <span class="adm-toolbar__spacer" />
        <span class="adm-muted">共 {{ data.tasksTotal }} 条任务</span>
      </div>

      <div v-if="filteredTasks.length" class="adm-table-wrap">
        <table class="adm-table">
          <thead>
            <tr>
              <th>任务 / 题目</th>
              <th>阶段</th>
              <th>状态</th>
              <th>重试</th>
              <th>创建时间</th>
              <th>耗时</th>
              <th />
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in filteredTasks" :key="task.id">
              <td>
                <div class="adm-table__excerpt">{{ task.question }}</div>
                <div class="adm-table__sub"><span class="adm-mono">{{ task.code }}</span> · {{ task.username }}</div>
              </td>
              <td>{{ stageLabel(task) }}</td>
              <td><StatusTag :tone="statusTone(task)" :label="statusLabel(task)" /></td>
              <td class="adm-mono">{{ task.retryIndex }}</td>
              <td class="adm-mono">{{ task.createdAt }}</td>
              <td>{{ task.duration }}</td>
              <td class="adm-table__right">
                <div class="adm-table__actions">
                  <button
                    v-if="task.status === 'failed'"
                    class="adm-btn adm-btn--primary adm-btn--sm"
                    type="button"
                    :disabled="busyTaskId === task.id"
                    @click="retryTask(task)"
                  >
                    重试
                  </button>
                  <button
                    v-else-if="task.status === 'queued'"
                    class="adm-btn adm-btn--quiet adm-btn--sm"
                    type="button"
                    :disabled="busyTaskId === task.id"
                    @click="cancelTask(task)"
                  >
                    取消
                  </button>
                  <button class="adm-btn adm-btn--quiet adm-btn--sm" type="button" @click="openTask(task)">详情</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="adm-empty">
        <strong>没有匹配的任务</strong>
        <p>换一个关键词或状态。</p>
      </div>
    </section>

    <a-drawer v-model:visible="drawerVisible" width="min(460px, 100vw)" :footer="false" title="任务详情">
      <div v-if="detailLoading" class="adm-empty">
        <strong>正在加载任务详情</strong>
        <p>GET /admin/tasks/{id}</p>
      </div>
      <template v-else-if="detail">
        <div class="adm-table__primary">{{ detail.question }}</div>
        <div class="adm-table__sub"><span class="adm-mono">{{ detail.code }}</span> · {{ detail.username }}</div>

        <div class="adm-detail-grid" style="margin-top: 16px">
          <dl class="adm-detail-item"><dt>阶段</dt><dd>{{ stageLabel(detail) }}</dd></dl>
          <dl class="adm-detail-item"><dt>状态</dt><dd>{{ statusLabel(detail) }}</dd></dl>
          <dl class="adm-detail-item"><dt>重试次数</dt><dd class="adm-mono">{{ detail.retryIndex }}</dd></dl>
          <dl class="adm-detail-item"><dt>耗时</dt><dd>{{ detail.duration }}</dd></dl>
          <dl class="adm-detail-item"><dt>创建时间</dt><dd class="adm-mono">{{ detail.createdAt }}</dd></dl>
          <dl class="adm-detail-item"><dt>错误码</dt><dd class="adm-mono">{{ detail.errorCode ?? '—' }}</dd></dl>
          <dl class="adm-detail-item"><dt>开始时间</dt><dd class="adm-mono">{{ detail.startedAt ?? '—' }}</dd></dl>
          <dl class="adm-detail-item"><dt>结束时间</dt><dd class="adm-mono">{{ detail.finishedAt ?? '—' }}</dd></dl>
        </div>

        <div v-if="detail.errorMessage" class="adm-warning-box" style="margin-top: 14px">
          <AppIcon name="warning" :size="15" />
          <span>{{ detail.errorCode }} · {{ detail.errorMessage }}</span>
        </div>

        <div class="adm-detail-section">
          <h3>处理时间线</h3>
          <ul v-if="detail.timeline?.length" class="adm-timeline">
            <li v-for="entry in detail.timeline ?? []" :key="entry.key">
              <span class="adm-timeline__dot" />
              <p class="adm-timeline__title">{{ entry.title }}</p>
              <p class="adm-timeline__meta">
                <time>{{ entry.time }}</time>
                <span>{{ entry.status }}</span>
                <span v-if="entry.meta">{{ entry.meta }}</span>
              </p>
            </li>
          </ul>
          <div v-else class="adm-muted">后端未返回时间线。</div>
        </div>

        <div class="adm-detail-section">
          <h3>操作</h3>
          <div class="adm-modal-actions" style="justify-content: flex-start">
            <button
              v-if="detail.status === 'failed'"
              class="adm-btn adm-btn--primary"
              type="button"
              :disabled="busyTaskId === detail.id"
              @click="retryTask(detail)"
            >
              重试任务
            </button>
            <button
              v-else-if="detail.status === 'queued'"
              class="adm-btn adm-btn--outline"
              type="button"
              :disabled="busyTaskId === detail.id"
              @click="cancelTask(detail)"
            >
              取消排队
            </button>
            <RouterLink class="adm-btn adm-btn--quiet" to="/ai-logs">查看 AI 调用日志</RouterLink>
          </div>
          <p class="adm-muted" style="margin-top: 10px">任务操作会写入审计日志。</p>
        </div>
      </template>
    </a-drawer>
  </div>
</template>
