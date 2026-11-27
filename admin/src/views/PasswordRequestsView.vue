<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Message } from '@arco-design/web-vue'

import AdminPageHeader from '../components/AdminPageHeader.vue'
import AppIcon from '../components/AppIcon.vue'
import MetricCard from '../components/MetricCard.vue'
import PasswordResetModal from '../components/PasswordResetModal.vue'
import StatusTag from '../components/StatusTag.vue'
import { useAdminData } from '../stores/adminData'
import type { PasswordApproveResult, PasswordRequest } from '../types'

type TabKey = 'pending' | 'approved' | 'rejected'

const data = useAdminData()

const activeTab = ref<TabKey>('pending')
const approveVisible = ref(false)
const selectedRequest = ref<PasswordRequest | null>(null)
const rejectVisible = ref(false)
const rejectTarget = ref<PasswordRequest | null>(null)
const rejectReason = ref('')
const rejectBusy = ref(false)

const regenerateVisible = ref(false)
const regenerateResult = ref<PasswordApproveResult | null>(null)
const regeneratingId = ref<number | null>(null)

const tabs: { key: TabKey; label: string }[] = [
  { key: 'pending', label: '待审批' },
  { key: 'approved', label: '已通过' },
  { key: 'rejected', label: '已拒绝' },
]

const counts = computed(() => ({
  pending: data.passwordRequests.filter((request) => request.status === 'pending').length,
  approved: data.passwordRequests.filter((request) => request.status === 'approved').length,
  rejected: data.passwordRequests.filter((request) => request.status === 'rejected').length,
}))

const visibleRequests = computed(() =>
  data.passwordRequests.filter((request) => request.status === activeTab.value),
)

const passwordStats = computed(() => data.overview?.stats.password_requests ?? null)

function errorText(cause: unknown): string {
  return cause instanceof Error ? cause.message : '操作失败，请稍后重试'
}

async function load(): Promise<void> {
  try {
    await data.loadPasswordRequests({ status: 'all' })
  } catch (cause) {
    Message.error(errorText(cause))
  }
}

onMounted(load)

function openApprove(request: PasswordRequest): void {
  selectedRequest.value = request
  approveVisible.value = true
}

function handleApproved(request: PasswordRequest): void {
  Message.success(`已通过 ${request.username} 的密码申请，临时密码仅显示一次`)
}

function openReject(request: PasswordRequest): void {
  rejectTarget.value = request
  rejectReason.value = ''
  rejectVisible.value = true
}

async function confirmReject(): Promise<void> {
  const target = rejectTarget.value
  if (!target) return
  if (rejectReason.value.trim().length < 4) {
    Message.error('请填写至少 4 个字的拒绝原因')
    return
  }
  rejectBusy.value = true
  try {
    await data.rejectPasswordRequest(target.id, rejectReason.value.trim())
    Message.success(`已拒绝 ${target.username} 的申请`)
    rejectVisible.value = false
  } catch (cause) {
    Message.error(errorText(cause))
  } finally {
    rejectBusy.value = false
  }
}

async function regenerate(request: PasswordRequest): Promise<void> {
  if (regeneratingId.value !== null) return
  regeneratingId.value = request.id
  try {
    const result = await data.regenerateTempPassword(request.id)
    regenerateResult.value = result
    regenerateVisible.value = true
    Message.success(`已重新生成 ${request.username} 的临时密码`)
  } catch (cause) {
    Message.error(errorText(cause))
  } finally {
    regeneratingId.value = null
  }
}

function statusLabel(status: PasswordRequest['status']): string {
  if (status === 'pending') return '待审批'
  if (status === 'approved') return '已通过'
  return '已拒绝'
}
</script>

<template>
  <div class="adm-page">
    <AdminPageHeader
      eyebrow="运营 · 密码申请"
      title="密码申请"
      description="学生线上提交，管理员核验用户名与注册邮箱后审批。临时密码只在管理端显示一次。"
    />

    <section class="adm-kpi-grid" aria-label="密码申请概览">
      <MetricCard
        label="待审批"
        :value="String(passwordStats?.pending ?? counts.pending)"
        hint="仅待审批申请可操作"
        :trend="(passwordStats?.pending ?? counts.pending) > 0 ? '需处理' : '空闲'"
        :trend-tone="(passwordStats?.pending ?? counts.pending) > 0 ? 'negative' : 'neutral'"
        icon="key"
      />
      <MetricCard
        label="今日通过"
        :value="String(passwordStats?.approved_today ?? '—')"
        hint="临时密码 24h 有效"
        icon="check"
      />
      <MetricCard
        label="今日拒绝"
        :value="String(passwordStats?.rejected_today ?? '—')"
        hint="信息不一致"
        icon="close"
      />
      <MetricCard label="平均处理时长" value="—" hint="接口未提供" icon="clock" />
    </section>

    <div class="adm-info-box">
      <AppIcon name="shield" :size="15" />
      <span>流程：学生提交 username + 可选邮箱 + 原因 → 管理员核验 → 系统生成一次性临时密码（24h）→ 学生登录后强制改密。</span>
    </div>

    <section class="adm-panel">
      <div class="adm-toolbar">
        <div class="adm-seg" role="tablist" aria-label="申请状态">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            role="tab"
            :aria-selected="activeTab === tab.key"
            :class="{ 'is-active': activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            {{ tab.label }} {{ counts[tab.key] }}
          </button>
        </div>
        <span class="adm-toolbar__spacer" />
        <span class="adm-muted">审批动作会写入审计</span>
      </div>

      <div v-if="visibleRequests.length" class="adm-table-wrap">
        <table class="adm-table">
          <thead>
            <tr>
              <th>申请人</th>
              <th>申请原因</th>
              <th>提交时间 / IP</th>
              <th>状态</th>
              <th>审批人</th>
              <th />
            </tr>
          </thead>
          <tbody>
            <tr v-for="request in visibleRequests" :key="request.id">
              <td>
                <div class="adm-user-cell">
                  <span class="adm-avatar">{{ request.username.slice(-2).toUpperCase() }}</span>
                  <div>
                    <div class="adm-table__primary">{{ request.username }}</div>
                    <div class="adm-table__sub">提交：{{ request.email || '未填写' }}</div>
                    <div class="adm-table__sub">注册：{{ request.registeredEmail || '未登记' }}</div>
                  </div>
                </div>
              </td>
              <td>
                <div class="adm-table__excerpt" style="max-width: 300px">{{ request.reason }}</div>
                <div v-if="request.reviewNote" class="adm-table__sub">{{ request.reviewNote }}</div>
                <StatusTag
                  v-if="!request.emailMatches"
                  tone="warning"
                  label="邮箱不一致"
                  :dot="false"
                />
              </td>
              <td>
                <div class="adm-mono">{{ request.submittedAt }}</div>
                <div class="adm-table__sub adm-mono">{{ request.ip }}</div>
              </td>
              <td>
                <StatusTag
                  :tone="request.status === 'pending' ? 'warning' : request.status === 'approved' ? 'success' : 'danger'"
                  :label="statusLabel(request.status)"
                />
              </td>
              <td>
                <div>{{ request.reviewedBy || '—' }}</div>
                <div v-if="request.reviewedAt" class="adm-table__sub adm-mono">{{ request.reviewedAt }}</div>
              </td>
              <td class="adm-table__right">
                <div v-if="request.status === 'pending'" class="adm-table__actions">
                  <button class="adm-btn adm-btn--primary adm-btn--sm" type="button" @click="openApprove(request)">
                    审批通过
                  </button>
                  <button class="adm-btn adm-btn--quiet adm-btn--sm" type="button" @click="openReject(request)">
                    拒绝
                  </button>
                </div>
                <button
                  v-else-if="request.status === 'approved'"
                  class="adm-btn adm-btn--quiet adm-btn--sm"
                  type="button"
                  :disabled="regeneratingId === request.id"
                  @click="regenerate(request)"
                >
                  {{ regeneratingId === request.id ? '生成中…' : '重发临时密码' }}
                </button>
                <span v-else class="adm-muted">已处理</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="adm-empty">
        <strong>没有{{ activeTab === 'pending' ? '待审批' : '' }}申请</strong>
        <p>切换状态查看历史记录。</p>
      </div>
    </section>

    <PasswordResetModal
      v-model:visible="approveVisible"
      :request="selectedRequest"
      @approved="handleApproved"
    />

    <a-modal v-model:visible="rejectVisible" title="拒绝密码申请" :footer="false" :width="440">
      <div class="adm-approval">
        <div class="adm-approval__user">
          <span class="adm-avatar adm-avatar--lg">{{ rejectTarget?.username.slice(-2).toUpperCase() }}</span>
          <div>
            <strong>{{ rejectTarget?.username }}</strong>
            <span>提交：{{ rejectTarget?.email || '未填写' }}</span>
            <span>注册：{{ rejectTarget?.registeredEmail || '未登记' }}</span>
          </div>
        </div>
        <div class="adm-field">
          <label for="reject-reason">拒绝原因（必填）</label>
          <a-textarea
            id="reject-reason"
            v-model="rejectReason"
            placeholder="例如：提交邮箱与账号登记邮箱不一致，请重新提交。"
            :auto-size="{ minRows: 3, maxRows: 5 }"
          />
        </div>
        <div class="adm-modal-actions">
          <button class="adm-btn adm-btn--outline" type="button" @click="rejectVisible = false">取消</button>
          <button class="adm-btn adm-btn--danger" type="button" :disabled="rejectBusy" @click="confirmReject">
            {{ rejectBusy ? '正在提交…' : '确认拒绝' }}
          </button>
        </div>
      </div>
    </a-modal>

    <a-modal v-model:visible="regenerateVisible" title="新的临时密码" :footer="false" :width="460">
      <div v-if="regenerateResult" class="adm-approval">
        <div class="adm-approval__result-head">
          <span class="adm-success-mark"><AppIcon name="check" :size="20" /></span>
          <div>
            <strong>{{ regenerateResult.request.username }} 的临时密码已重发</strong>
            <span>旧临时密码已失效，关闭后无法再次查看。</span>
          </div>
        </div>
        <div class="adm-temp-password">
          <code>{{ regenerateResult.temporary_password }}</code>
        </div>
        <div class="adm-info-box">
          <AppIcon name="clock" :size="15" />
          <span>有效期至 {{ regenerateResult.expires_at }}，学生登录后必须改密。</span>
        </div>
        <div class="adm-modal-actions">
          <button class="adm-btn adm-btn--primary" type="button" @click="regenerateVisible = false">我已记录，关闭</button>
        </div>
      </div>
    </a-modal>
  </div>
</template>
