<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Message } from '@arco-design/web-vue'

import AdminPageHeader from '../components/AdminPageHeader.vue'
import AppIcon from '../components/AppIcon.vue'
import StatusTag from '../components/StatusTag.vue'
import { useAdminData } from '../stores/adminData'
import type { SystemCheck } from '../types'

const data = useAdminData()
const refreshing = ref(false)

const system = computed(() => data.system)

interface HealthItem {
  name: string
  label: string
  tone: 'success' | 'warning' | 'danger' | 'neutral'
  value: string
  detail: string
}

function checkTone(status: string): HealthItem['tone'] {
  if (status === 'ok') return 'success'
  if (status === 'warning') return 'warning'
  if (status === 'error' || status === 'critical') return 'danger'
  return 'neutral'
}

function statusLabel(status: string): string {
  if (status === 'ok') return '正常'
  if (status === 'warning') return '警告'
  if (status === 'error') return '异常'
  return status || '未知'
}

function toHealthItem(check: SystemCheck): HealthItem {
  return {
    name: check.name,
    label: statusLabel(check.status),
    tone: checkTone(check.status),
    value: check.value,
    detail: check.detail,
  }
}

const healthItems = computed<HealthItem[]>(() =>
  system.value ? (system.value.checks ?? []).map(toHealthItem) : [],
)

const configRows = computed(() =>
  (system.value?.config ?? []).map((row) => ({ key: row.label, value: row.value, note: row.note })),
)

const eventTone = (level: string): string =>
  level === 'error' ? 'var(--adm-red)' : level === 'warning' ? 'var(--adm-amber)' : 'var(--adm-green)'

function errorText(cause: unknown): string {
  return cause instanceof Error ? cause.message : '系统信息加载失败'
}

async function load(): Promise<void> {
  try {
    await data.loadSystem()
  } catch (cause) {
    Message.error(errorText(cause))
  }
}

async function refresh(): Promise<void> {
  if (refreshing.value) return
  refreshing.value = true
  try {
    await data.loadSystem()
    Message.success('健康检查已刷新')
  } catch (cause) {
    Message.error(errorText(cause))
  } finally {
    refreshing.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="adm-page">
    <AdminPageHeader
      eyebrow="系统 · 健康"
      title="系统健康"
      description="DB、Worker、LLM 与部署环境的只读视图；配置变更仍通过环境变量与部署完成。"
    >
      <template #actions>
        <button class="adm-btn adm-btn--outline" type="button" :disabled="refreshing" @click="refresh">
          <AppIcon name="refresh" :size="15" />
          {{ refreshing ? '刷新中…' : '刷新' }}
        </button>
      </template>
    </AdminPageHeader>

    <section v-if="healthItems.length" class="adm-health-grid" aria-label="系统健康">
      <article v-for="item in healthItems" :key="item.name" class="adm-health-card">
        <div class="adm-health-card__top">
          <span>{{ item.name }}</span>
          <StatusTag :tone="item.tone" :label="item.label" />
        </div>
        <strong>{{ item.value }}</strong>
        <p>{{ item.detail }}</p>
      </article>
    </section>
    <div v-else class="adm-empty">
      <strong>尚未获取系统健康数据</strong>
      <p>确认已登录且后端 /admin/system 可访问。</p>
    </div>

    <div class="adm-split">
      <section class="adm-panel">
        <div class="adm-panel__head">
          <h2>只读配置</h2>
          <span class="adm-muted">{{ system?.environment.app_env ?? '—' }} · 生成于 {{ system?.generated_at ?? '—' }}</span>
        </div>
        <div class="adm-table-wrap">
          <table class="adm-table">
            <tbody>
              <tr v-for="row in configRows" :key="row.key">
                <td style="width: 42%; color: var(--adm-ink-3)">{{ row.key }}</td>
                <td class="adm-mono">{{ row.value }}<span v-if="row.note" class="adm-table__sub"> · {{ row.note }}</span></td>
              </tr>
              <tr v-if="!configRows.length">
                <td colspan="2" class="adm-muted">接口未返回配置项。</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="adm-panel__body" style="padding-top: 12px">
          <div class="adm-info-box">
            <AppIcon name="shield" :size="15" />
            <span>配置修改走环境变量/部署；admin 不直接编辑 .env，不展示 API Key、JWT Secret 或数据库密码。</span>
          </div>
        </div>
      </section>

      <section class="adm-panel">
        <div class="adm-panel__head">
          <h2>最近事件</h2>
          <span class="adm-muted">{{ system?.status.summary ?? '—' }}</span>
        </div>
        <ul class="adm-timeline" style="padding-top: 10px">
          <li v-for="event in system?.events ?? []" :key="`${event.time}-${event.title}`">
            <span class="adm-timeline__dot" :style="{ background: eventTone(event.level) }" />
            <p class="adm-timeline__title">{{ event.title }}</p>
            <p class="adm-timeline__meta"><time>{{ event.time }}</time><span>{{ event.detail }}</span></p>
          </li>
          <li v-if="!system?.events?.length">
            <span class="adm-timeline__dot" />
            <p class="adm-timeline__title">暂无事件</p>
            <p class="adm-timeline__meta"><span>—</span></p>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
