<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'

import AdminPageHeader from '../components/AdminPageHeader.vue'
import AppIcon from '../components/AppIcon.vue'
import MetricCard from '../components/MetricCard.vue'
import StatusTag from '../components/StatusTag.vue'
import { useAdminData } from '../stores/adminData'
import type { AuditLog } from '../types'

type ResultFilter = 'all' | AuditLog['result']

const data = useAdminData()

const keyword = ref('')
const result = ref<ResultFilter>('all')
const drawerVisible = ref(false)
const detail = ref<AuditLog | null>(null)
const detailLoading = ref(false)
const exporting = ref(false)

let filterTimer: number | undefined

const actionLabels: Record<string, string> = {
  'admin.login': '管理员登录',
  'admin.logout': '管理员登出',
  'user.disable': '禁用用户',
  'user.enable': '启用用户',
  'user.force_logout': '强制下线',
  'task.retry': '重试任务',
  'task.cancel': '取消任务',
  'password_request.approve': '通过密码申请',
  'password_request.reject': '拒绝密码申请',
  'password_request.regenerate': '重发临时密码',
  'question.hide': '隐藏内容',
  'question.restore': '恢复内容',
  'question.flag': '标记内容',
  'question.unflag': '取消标记',
  'question.soft_delete': '软删除内容',
  'ai_log.view_raw': '查看 AI 原始输出',
  'audit.export': '导出审计日志',
}

const filteredLogs = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  return data.auditLogs.filter((log) => {
    if (result.value !== 'all' && log.result !== result.value) return false
    if (!query) return true
    return `${log.admin} ${log.action} ${log.target} ${log.reason} ${log.ip} ${log.requestId}`
      .toLowerCase()
      .includes(query)
  })
})

function errorText(cause: unknown): string {
  return cause instanceof Error ? cause.message : '操作失败，请稍后重试'
}

async function load(): Promise<void> {
  try {
    await data.loadAuditLogs({
      q: keyword.value.trim() || undefined,
      result: result.value === 'all' ? undefined : result.value,
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

watch([keyword, result], scheduleLoad)
onMounted(load)
onUnmounted(() => {
  if (filterTimer) window.clearTimeout(filterTimer)
})

async function openLog(log: AuditLog): Promise<void> {
  drawerVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await data.loadAuditDetail(log.id)
  } catch (cause) {
    Message.error(errorText(cause))
    drawerVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

function formatJson(value: Record<string, unknown> | null): string {
  return value ? JSON.stringify(value, null, 2) : '—'
}

async function exportAudit(): Promise<void> {
  if (exporting.value) return
  exporting.value = true
  try {
    const blob = await data.exportAuditCsv({
      q: keyword.value.trim() || undefined,
      result: result.value === 'all' ? undefined : result.value,
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'bababoi-audit.csv'
    link.click()
    URL.revokeObjectURL(url)
    Message.success('审计日志已导出')
  } catch (cause) {
    Message.error(errorText(cause))
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <div class="adm-page">
    <AdminPageHeader
      eyebrow="审计 · 操作"
      title="审计日志"
      description="所有管理员写操作与敏感读取都在这里留痕。审计 append-only，不提供删除入口。"
    >
      <template #actions>
        <button class="adm-btn adm-btn--outline" type="button" :disabled="exporting" @click="exportAudit">
          <AppIcon name="download" :size="15" />
          {{ exporting ? '导出中…' : '导出' }}
        </button>
      </template>
    </AdminPageHeader>

    <section class="adm-kpi-grid" aria-label="审计概览">
      <MetricCard label="今日操作" value="—" hint="接口未提供聚合" icon="audit" />
      <MetricCard label="敏感读取" value="—" hint="查看 raw 写入审计" icon="shield" />
      <MetricCard label="失败操作" value="—" hint="可用结果筛选查看" icon="check" />
      <MetricCard label="保留策略" value="—" hint="append-only" icon="clock" />
    </section>

    <section class="adm-panel">
      <div class="adm-toolbar">
        <a-input v-model="keyword" class="adm-search" placeholder="搜索管理员、动作、目标或原因" allow-clear>
          <template #prefix><AppIcon name="search" :size="14" /></template>
        </a-input>
        <a-select v-model="result" class="adm-filter" aria-label="结果筛选">
          <a-option value="all">全部结果</a-option>
          <a-option value="success">成功</a-option>
          <a-option value="failed">失败</a-option>
        </a-select>
        <span class="adm-toolbar__spacer" />
        <span class="adm-muted">共 {{ data.auditTotal }} 条记录</span>
      </div>

      <div v-if="filteredLogs.length" class="adm-table-wrap">
        <table class="adm-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>管理员</th>
              <th>动作</th>
              <th>目标</th>
              <th>原因</th>
              <th>结果</th>
              <th>IP</th>
              <th />
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in filteredLogs" :key="log.id">
              <td class="adm-mono">{{ log.time }}</td>
              <td>{{ log.admin }}</td>
              <td>
                <div class="adm-table__primary">{{ actionLabels[log.action] ?? log.action }}</div>
                <div class="adm-table__sub adm-mono">{{ log.action }}</div>
              </td>
              <td class="adm-mono">{{ log.target }}</td>
              <td><div class="adm-table__excerpt" style="max-width: 280px">{{ log.reason }}</div></td>
              <td><StatusTag :tone="log.result === 'success' ? 'success' : 'danger'" :label="log.result === 'success' ? '成功' : '失败'" /></td>
              <td class="adm-mono">{{ log.ip }}</td>
              <td class="adm-table__right">
                <button class="adm-btn adm-btn--quiet adm-btn--sm" type="button" @click="openLog(log)">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="adm-empty">
        <strong>没有匹配的审计记录</strong>
        <p>换一个关键词或结果。</p>
      </div>
    </section>

    <a-drawer v-model:visible="drawerVisible" width="min(440px, 100vw)" :footer="false" title="审计详情">
      <div v-if="detailLoading" class="adm-empty">
        <strong>正在加载审计详情</strong>
        <p>GET /admin/audit/{id}</p>
      </div>
      <template v-else-if="detail">
        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap">
          <StatusTag :tone="detail.result === 'success' ? 'success' : 'danger'" :label="detail.result === 'success' ? '成功' : '失败'" />
          <span class="adm-muted adm-mono">audit#{{ detail.id }}</span>
        </div>

        <div class="adm-detail-grid" style="margin-top: 16px">
          <dl class="adm-detail-item"><dt>时间</dt><dd class="adm-mono">{{ detail.time }}</dd></dl>
          <dl class="adm-detail-item"><dt>管理员</dt><dd>{{ detail.admin }}</dd></dl>
          <dl class="adm-detail-item"><dt>动作</dt><dd>{{ actionLabels[detail.action] ?? detail.action }}</dd></dl>
          <dl class="adm-detail-item"><dt>目标</dt><dd class="adm-mono">{{ detail.target }}</dd></dl>
          <dl class="adm-detail-item"><dt>目标类型</dt><dd>{{ detail.targetType ?? '—' }}<span v-if="detail.targetId"> · #{{ detail.targetId }}</span></dd></dl>
          <dl class="adm-detail-item"><dt>来源 IP</dt><dd class="adm-mono">{{ detail.ip }}</dd></dl>
          <dl class="adm-detail-item"><dt>Request ID</dt><dd class="adm-mono">{{ detail.requestId }}</dd></dl>
        </div>

        <div class="adm-detail-section">
          <h3>操作原因</h3>
          <div class="adm-detail-copy">{{ detail.reason }}</div>
        </div>

        <div v-if="detail.errorMessage" class="adm-warning-box" style="margin-top: 14px">
          <AppIcon name="warning" :size="15" />
          <span>{{ detail.errorMessage }}</span>
        </div>

        <div class="adm-detail-section">
          <h3>变更前 (before)</h3>
          <pre class="adm-code-block">{{ formatJson(detail.before) }}</pre>
        </div>

        <div class="adm-detail-section">
          <h3>变更后 (after)</h3>
          <pre class="adm-code-block">{{ formatJson(detail.after) }}</pre>
        </div>

        <div class="adm-info-box" style="margin-top: 14px">
          <AppIcon name="shield" :size="15" />
          <span>审计记录只读。before/after 已脱敏，不包含密码、Key 或完整学生内容。</span>
        </div>
      </template>
    </a-drawer>
  </div>
</template>
