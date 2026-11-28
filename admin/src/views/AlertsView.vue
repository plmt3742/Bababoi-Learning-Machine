<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { RouterLink } from 'vue-router'

import AdminPageHeader from '../components/AdminPageHeader.vue'
import AppIcon from '../components/AppIcon.vue'
import MetricCard from '../components/MetricCard.vue'
import StatusTag from '../components/StatusTag.vue'
import { useAdminData } from '../stores/adminData'
import type { AlertItem } from '../types'

type TabKey = 'active' | 'acknowledged' | 'all'

const data = useAdminData()

const tab = ref<TabKey>('active')
const busyAlert = ref<string | null>(null)

const visibleAlerts = computed(() => {
  if (tab.value === 'all') return data.alerts
  return data.alerts.filter((alert) => alert.status === tab.value)
})

const acknowledgedCount = computed(
  () => data.alerts.filter((alert) => alert.status === 'acknowledged').length,
)

function severityTone(severity: AlertItem['severity']): 'danger' | 'warning' | 'info' {
  if (severity === 'critical') return 'danger'
  if (severity === 'warning') return 'warning'
  return 'info'
}

function severityLabel(severity: AlertItem['severity']): string {
  if (severity === 'critical') return '严重'
  if (severity === 'warning') return '警告'
  return '提示'
}

function errorText(cause: unknown): string {
  return cause instanceof Error ? cause.message : '操作失败，请稍后重试'
}

async function load(): Promise<void> {
  try {
    await data.loadAlerts()
  } catch (cause) {
    Message.error(errorText(cause))
  }
}

onMounted(load)

async function acknowledge(alert: AlertItem): Promise<void> {
  if (busyAlert.value !== null) return
  busyAlert.value = alert.id
  try {
    await data.ackAlert(alert.id)
    Message.success(`已确认：${alert.title}`)
  } catch (cause) {
    Message.error(errorText(cause))
  } finally {
    busyAlert.value = null
  }
}

async function unacknowledge(alert: AlertItem): Promise<void> {
  if (busyAlert.value !== null) return
  busyAlert.value = alert.id
  try {
    await data.unackAlert(alert.id)
    Message.success(`已取消确认：${alert.title}`)
  } catch (cause) {
    Message.error(errorText(cause))
  } finally {
    busyAlert.value = null
  }
}

const rules = [
  { title: '任务失败率', detail: '15 分钟内失败任务 ≥ 3 个，或失败率 > 10%', severity: 'critical' as const },
  { title: '队列积压', detail: '最老 queued 任务等待超过阈值', severity: 'warning' as const },
  { title: 'AI 延迟', detail: '1 小时内 P95 延迟 > 45 秒', severity: 'warning' as const },
  { title: 'AI 错误率', detail: '1 小时内 error + invalid > 10%', severity: 'critical' as const },
  { title: '密码申请积压', detail: '存在待审批密码申请', severity: 'warning' as const },
]
</script>

<template>
  <div class="adm-page">
    <AdminPageHeader
      eyebrow="监控 · 告警"
      title="告警中心"
      description="把失败任务、队列积压、AI 延迟与系统健康放在同一处；MVP 先做页面告警，P2 再接 webhook。"
    />

    <section class="adm-kpi-grid" aria-label="告警概览">
      <MetricCard
        label="活跃告警"
        :value="String(data.activeAlertCount)"
        :hint="data.activeAlertCount > 0 ? '需处理' : '当前无活跃告警'"
        :trend="data.activeAlertCount > 0 ? '需处理' : '正常'"
        :trend-tone="data.activeAlertCount > 0 ? 'negative' : 'neutral'"
        :danger="data.activeAlertCount > 0"
        icon="alert"
      />
      <MetricCard label="已确认" :value="String(acknowledgedCount)" hint="当前已确认条件" icon="check" />
      <MetricCard label="本周触发" value="—" hint="接口未提供历史" icon="clock" />
      <MetricCard label="平均确认时长" value="—" hint="接口未提供" icon="system" />
    </section>

    <div class="adm-split">
      <section class="adm-panel">
        <div class="adm-toolbar">
          <div class="adm-seg" role="tablist" aria-label="告警状态">
            <button type="button" :class="{ 'is-active': tab === 'active' }" @click="tab = 'active'">活跃</button>
            <button type="button" :class="{ 'is-active': tab === 'acknowledged' }" @click="tab = 'acknowledged'">已确认</button>
            <button type="button" :class="{ 'is-active': tab === 'all' }" @click="tab = 'all'">全部</button>
          </div>
          <span class="adm-toolbar__spacer" />
          <span class="adm-muted">页面告警 · 不阻塞业务</span>
        </div>

        <ul v-if="visibleAlerts.length" class="adm-rule-list" style="padding: 0 18px">
          <li v-for="alert in visibleAlerts" :key="alert.id">
            <span class="adm-rule-list__badge" :class="`adm-rule-list__badge--${alert.severity}`" />
            <div style="min-width: 0">
              <strong>{{ alert.title }}</strong>
              <span>{{ alert.detail }}</span>
              <span class="adm-mono" style="margin-top: 4px">
                {{ alert.time }} · 当前 {{ alert.current }} / 阈值 {{ alert.threshold }} · {{ alert.rule }}
              </span>
              <RouterLink v-if="alert.target" class="adm-link" :to="alert.target.to" style="margin-top: 4px">
                {{ alert.target.label }} →
              </RouterLink>
            </div>
            <div class="adm-rule-list__action">
              <StatusTag :tone="severityTone(alert.severity)" :label="severityLabel(alert.severity)" />
              <button
                v-if="alert.status === 'active'"
                class="adm-btn adm-btn--quiet adm-btn--sm"
                type="button"
                style="margin-left: 8px"
                :disabled="busyAlert === alert.id"
                @click="acknowledge(alert)"
              >
                确认
              </button>
              <button
                v-else
                class="adm-btn adm-btn--quiet adm-btn--sm"
                type="button"
                style="margin-left: 8px"
                :disabled="busyAlert === alert.id"
                @click="unacknowledge(alert)"
              >
                取消确认
              </button>
            </div>
          </li>
        </ul>
        <div v-else class="adm-empty">
          <strong>当前没有{{ tab === 'active' ? '活跃' : '匹配的' }}告警</strong>
          <p>系统运行正常。</p>
        </div>
      </section>

      <section class="adm-panel">
        <div class="adm-panel__head">
          <h2>告警规则</h2>
          <span class="adm-muted">后端派生</span>
        </div>
        <ul class="adm-rule-list">
          <li v-for="rule in rules" :key="rule.title">
            <span class="adm-rule-list__badge" :class="`adm-rule-list__badge--${rule.severity}`" />
            <div>
              <strong>{{ rule.title }}</strong>
              <span>{{ rule.detail }}</span>
            </div>
          </li>
        </ul>
        <div class="adm-panel__body" style="padding-top: 0">
          <div class="adm-info-box">
            <AppIcon name="shield" :size="15" />
            <span>告警由后端根据真实任务 / AI 调用 / 密码申请派生；确认状态写入 admin_alert_acks。P2 再接飞书/企业微信 webhook。</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
