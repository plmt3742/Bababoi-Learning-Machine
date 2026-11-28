<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'

import AdminPageHeader from '../components/AdminPageHeader.vue'
import AppIcon from '../components/AppIcon.vue'
import MetricCard from '../components/MetricCard.vue'
import StatusTag from '../components/StatusTag.vue'
import { useAdminData } from '../stores/adminData'
import type { AiLog } from '../types'

type StatusFilter = 'all' | AiLog['status']
type OperationFilter = 'all' | AiLog['operation']

const data = useAdminData()

const keyword = ref('')
const operation = ref<OperationFilter>('all')
const status = ref<StatusFilter>('all')
const drawerVisible = ref(false)
const detail = ref<AiLog | null>(null)
const detailLoading = ref(false)

const rawReason = ref('')
const revealedRaw = ref('')
const rawLoaded = ref(false)
const rawTruncated = ref(false)
const rawAuditId = ref<number | null>(null)
const rawBusy = ref(false)

let filterTimer: number | undefined

const aiStats = computed(() => data.overview?.stats.ai ?? null)

const filteredLogs = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  return data.aiLogs.filter((log) => {
    if (operation.value !== 'all' && log.operation !== operation.value) return false
    if (status.value !== 'all' && log.status !== status.value) return false
    if (!query) return true
    return `${log.id} ${log.username} ${log.model} ${log.promptVersion} ${log.errorCode ?? ''}`
      .toLowerCase()
      .includes(query)
  })
})

const operationLabels: Record<AiLog['operation'], string> = {
  vision: '识图',
  analyze: '分析',
  generate: '生题',
  judge: '判分',
}

const statusLabels: Record<AiLog['status'], string> = {
  success: '成功',
  error: '失败',
  invalid: '无效输出',
}

function statusTone(log: AiLog): 'success' | 'danger' | 'warning' {
  if (log.status === 'success') return 'success'
  if (log.status === 'error') return 'danger'
  return 'warning'
}

function errorText(cause: unknown): string {
  return cause instanceof Error ? cause.message : '操作失败，请稍后重试'
}

async function load(): Promise<void> {
  try {
    await data.loadAiLogs({
      q: keyword.value.trim() || undefined,
      status: status.value === 'all' ? 'all' : status.value,
      operation: operation.value === 'all' ? undefined : operation.value,
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

watch([keyword, operation, status], scheduleLoad)
onMounted(load)
onUnmounted(() => {
  if (filterTimer) window.clearTimeout(filterTimer)
})

async function openLog(log: AiLog): Promise<void> {
  drawerVisible.value = true
  detailLoading.value = true
  detail.value = null
  rawReason.value = ''
  revealedRaw.value = ''
  rawLoaded.value = false
  rawTruncated.value = false
  rawAuditId.value = null
  try {
    detail.value = await data.loadAiLogDetail(log.id)
  } catch (cause) {
    Message.error(errorText(cause))
    drawerVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

async function revealRaw(): Promise<void> {
  const log = detail.value
  if (!log) return
  if (rawReason.value.trim().length < 2) {
    Message.error('请填写至少 2 个字的查看原因')
    return
  }
  rawBusy.value = true
  try {
    const result = await data.revealAiLogRaw(log.id, rawReason.value.trim())
    revealedRaw.value = result.raw
    rawLoaded.value = true
    rawTruncated.value = result.truncated
    rawAuditId.value = result.audit_id
    Message.success('已获取原始输出，本次查看已写入审计')
  } catch (cause) {
    Message.error(errorText(cause))
  } finally {
    rawBusy.value = false
  }
}

function csvCell(value: string | number): string {
  return `"${String(value).replace(/"/g, '""')}"`
}

function exportLogs(): void {
  const header = 'time,username,operation,model,status,latency,queue_wait,tokens,key_source,error_code\n'
  const body = filteredLogs.value
    .map((log) =>
      [
        log.time,
        log.username,
        log.operation,
        log.model,
        log.status,
        log.latency,
        log.queueWait,
        log.tokens,
        log.keySource,
        log.errorCode ?? '',
      ]
        .map(csvCell)
        .join(','),
    )
    .join('\n')
  const blob = new Blob([`\uFEFF${header}${body}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'bababoi-ai-logs.csv'
  link.click()
  URL.revokeObjectURL(url)
  Message.success('AI 调用日志已导出')
}
</script>

<template>
  <div class="adm-page">
    <AdminPageHeader
      eyebrow="AI 运维 · 调用"
      title="AI 调用日志"
      description="查看每次模型调用的状态、延迟、tokens 与 Key 来源。原始输出需单独展开并写审计。"
    >
      <template #actions>
        <button class="adm-btn adm-btn--outline" type="button" @click="exportLogs">
          <AppIcon name="download" :size="15" />
          导出
        </button>
      </template>
    </AdminPageHeader>

    <section class="adm-kpi-grid" aria-label="AI 调用概览">
      <MetricCard
        label="调用量 · 24h"
        :value="String(aiStats?.calls_24h ?? '—')"
        :hint="aiStats ? `error ${aiStats.error_rate}% · invalid ${aiStats.invalid_rate}%` : '加载中'"
        icon="spark"
      />
      <MetricCard
        label="成功率"
        :value="aiStats ? aiStats.success_rate.toFixed(1) : '—'"
        :unit="aiStats ? '%' : ''"
        hint="24h 窗口"
        icon="check"
      />
      <MetricCard
        label="P95 延迟"
        :value="aiStats ? (aiStats.p95_latency_ms / 1000).toFixed(1) : '—'"
        :unit="aiStats ? 's' : ''"
        :hint="aiStats ? `P50 ${(aiStats.p50_latency_ms / 1000).toFixed(1)}s` : '加载中'"
        icon="clock"
      />
      <MetricCard
        label="估算成本"
        :value="aiStats && aiStats.estimated_cost !== null ? `¥${aiStats.estimated_cost.toFixed(2)}` : '—'"
        :hint="aiStats ? `${aiStats.input_tokens + aiStats.output_tokens} tokens` : '加载中'"
        icon="system"
      />
    </section>

    <section class="adm-panel">
      <div class="adm-toolbar">
        <a-input v-model="keyword" class="adm-search" placeholder="搜索用户、模型、Prompt 或错误码" allow-clear>
          <template #prefix><AppIcon name="search" :size="14" /></template>
        </a-input>
        <a-select v-model="operation" class="adm-filter" aria-label="操作筛选">
          <a-option value="all">全部操作</a-option>
          <a-option value="vision">识图</a-option>
          <a-option value="analyze">分析</a-option>
          <a-option value="generate">生题</a-option>
          <a-option value="judge">判分</a-option>
        </a-select>
        <a-select v-model="status" class="adm-filter" aria-label="状态筛选">
          <a-option value="all">全部状态</a-option>
          <a-option value="success">成功</a-option>
          <a-option value="error">失败</a-option>
          <a-option value="invalid">无效输出</a-option>
        </a-select>
        <span class="adm-toolbar__spacer" />
        <span class="adm-muted">共 {{ data.aiLogsTotal }} 次调用</span>
      </div>

      <div v-if="filteredLogs.length" class="adm-table-wrap">
        <table class="adm-table">
          <thead>
            <tr>
              <th>时间 / 用户</th>
              <th>操作 / 模型</th>
              <th>状态</th>
              <th>延迟 / 排队</th>
              <th>Tokens</th>
              <th>Key</th>
              <th />
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in filteredLogs" :key="log.id">
              <td>
                <div class="adm-mono">{{ log.time }}</div>
                <div class="adm-table__sub">{{ log.username }}</div>
              </td>
              <td>
                <div>{{ operationLabels[log.operation] }}</div>
                <div class="adm-table__sub adm-mono">{{ log.model }} · {{ log.promptVersion }}</div>
              </td>
              <td><StatusTag :tone="statusTone(log)" :label="statusLabels[log.status]" /></td>
              <td class="adm-mono">{{ log.latency }} / {{ log.queueWait }}</td>
              <td class="adm-mono">{{ log.tokens }}</td>
              <td><span class="adm-tag adm-tag--neutral">{{ log.keySource }}</span></td>
              <td class="adm-table__right">
                <button class="adm-btn adm-btn--quiet adm-btn--sm" type="button" @click="openLog(log)">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="adm-empty">
        <strong>没有匹配的调用</strong>
        <p>换一个关键词或筛选条件。</p>
      </div>
    </section>

    <a-drawer v-model:visible="drawerVisible" width="min(500px, 100vw)" :footer="false" title="AI 调用详情">
      <div v-if="detailLoading" class="adm-empty">
        <strong>正在加载调用详情</strong>
        <p>GET /admin/ai-logs/{id}</p>
      </div>
      <template v-else-if="detail">
        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap">
          <StatusTag :tone="statusTone(detail)" :label="statusLabels[detail.status]" />
          <span class="adm-muted adm-mono">log#{{ detail.id }}</span>
        </div>

        <div class="adm-detail-grid" style="margin-top: 16px">
          <dl class="adm-detail-item"><dt>用户</dt><dd>{{ detail.username }}</dd></dl>
          <dl class="adm-detail-item"><dt>操作</dt><dd>{{ operationLabels[detail.operation] }}</dd></dl>
          <dl class="adm-detail-item"><dt>模型</dt><dd class="adm-mono">{{ detail.model }}</dd></dl>
          <dl class="adm-detail-item"><dt>Prompt 版本</dt><dd class="adm-mono">{{ detail.promptVersion }}</dd></dl>
          <dl class="adm-detail-item"><dt>延迟</dt><dd class="adm-mono">{{ detail.latency }}</dd></dl>
          <dl class="adm-detail-item"><dt>排队等待</dt><dd class="adm-mono">{{ detail.queueWait }}</dd></dl>
          <dl class="adm-detail-item"><dt>Tokens</dt><dd class="adm-mono">{{ detail.tokens }}</dd></dl>
          <dl class="adm-detail-item"><dt>Key 来源</dt><dd>{{ detail.keySource }}</dd></dl>
          <dl class="adm-detail-item"><dt>题目 ID</dt><dd class="adm-mono">{{ detail.questionId ?? '—' }}</dd></dl>
          <dl class="adm-detail-item"><dt>时间</dt><dd class="adm-mono">{{ detail.time }}</dd></dl>
        </div>

        <div v-if="detail.errorCode" class="adm-warning-box" style="margin-top: 14px">
          <AppIcon name="warning" :size="15" />
          <span>{{ detail.errorCode }} · 查看原始输出定位是 prompt 还是模型问题。</span>
        </div>

        <div class="adm-detail-section">
          <h3>原始输出</h3>
          <div v-if="!rawLoaded" class="adm-info-box">
            <AppIcon name="shield" :size="15" />
            <span>原始输出可能包含学生题目内容。展开动作会写入审计，列表与详情默认不返回。</span>
          </div>
          <template v-if="!rawLoaded">
            <div v-if="detail.hasRaw" class="adm-field" style="margin-top: 10px">
              <label for="raw-reason">查看原因（必填，至少 2 个字）</label>
              <a-input id="raw-reason" v-model="rawReason" placeholder="例如：排查 AI 超时" allow-clear />
            </div>
            <button
              v-if="detail.hasRaw"
              class="adm-btn adm-btn--outline"
              style="margin-top: 10px"
              type="button"
              :disabled="rawBusy"
              @click="revealRaw"
            >
              {{ rawBusy ? '正在获取…' : '展开原始输出' }}
            </button>
            <div v-else class="adm-muted" style="margin-top: 10px">本次调用没有可查看的原始输出。</div>
          </template>
          <template v-else>
            <div class="adm-info-box" style="margin-top: 10px">
              <AppIcon name="shield" :size="15" />
              <span>
                本次查看已写入审计{{ rawAuditId !== null ? `（audit#${rawAuditId}）` : '' }}。
                <template v-if="rawTruncated">内容超过 8000 字符，已截断。</template>
              </span>
            </div>
            <pre class="adm-code-block" style="margin-top: 10px">{{ revealedRaw }}</pre>
          </template>
        </div>
      </template>
    </a-drawer>
  </div>
</template>
