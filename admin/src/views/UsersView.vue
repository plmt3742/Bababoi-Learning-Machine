<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { RouterLink } from 'vue-router'

import AdminPageHeader from '../components/AdminPageHeader.vue'
import AppIcon from '../components/AppIcon.vue'
import StatusTag from '../components/StatusTag.vue'
import { useAdminData } from '../stores/adminData'
import type { AdminUser, AdminUserDetail } from '../types'

type StatusFilter = 'all' | 'active' | 'disabled'
type UserAction = 'disable' | 'enable' | 'force-logout'

const data = useAdminData()

const keyword = ref('')
const status = ref<StatusFilter>('all')
const drawerVisible = ref(false)
const detail = ref<AdminUserDetail | null>(null)
const detailLoading = ref(false)

const actionVisible = ref(false)
const actionUser = ref<AdminUser | null>(null)
const actionKind = ref<UserAction>('disable')
const actionReason = ref('')
const actionBusy = ref(false)

let filterTimer: number | undefined

const filteredUsers = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  return data.users.filter((user) => {
    if (status.value !== 'all' && user.status !== status.value) return false
    if (!query) return true
    return `${user.username} ${user.email}`.toLowerCase().includes(query)
  })
})

const actionTitle = computed(() => {
  if (actionKind.value === 'disable') return '禁用账号'
  if (actionKind.value === 'enable') return '启用账号'
  return '强制下线'
})

function errorText(cause: unknown): string {
  return cause instanceof Error ? cause.message : '操作失败，请稍后重试'
}

async function load(): Promise<void> {
  try {
    await data.loadUsers({
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

async function openUser(user: AdminUser): Promise<void> {
  drawerVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await data.loadUserDetail(user.id)
  } catch (cause) {
    Message.error(errorText(cause))
    drawerVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

function askAction(user: AdminUser, kind: UserAction): void {
  actionUser.value = user
  actionKind.value = kind
  actionReason.value = ''
  actionVisible.value = true
}

async function confirmAction(): Promise<void> {
  const user = actionUser.value
  if (!user) return
  actionBusy.value = true
  try {
    if (actionKind.value === 'force-logout') {
      await data.forceLogoutUser(user.id)
      Message.success(`已强制下线 ${user.username}，旧 token 将失效`)
    } else {
      const disabling = actionKind.value === 'disable'
      if (disabling && actionReason.value.trim().length < 4) {
        Message.error('请填写至少 4 个字的禁用原因')
        return
      }
      await data.setUserStatus(user.id, {
        status: disabling ? 'disabled' : 'active',
        reason: disabling ? actionReason.value.trim() : undefined,
      })
      Message.success(disabling ? `已禁用 ${user.username}` : `已启用 ${user.username}`)
    }
    actionVisible.value = false
    if (detail.value?.id === user.id) {
      detail.value = await data.loadUserDetail(user.id)
    }
  } catch (cause) {
    Message.error(errorText(cause))
  } finally {
    actionBusy.value = false
  }
}

function csvCell(value: string | number): string {
  return `"${String(value).replace(/"/g, '""')}"`
}

function exportUsers(): void {
  const header = 'username,email,status,questions,generated,practice,last_login\n'
  const body = filteredUsers.value
    .map((user) =>
      [
        user.username,
        user.email,
        user.status,
        user.questions,
        user.generated,
        user.practice,
        user.lastLogin,
      ]
        .map(csvCell)
        .join(','),
    )
    .join('\n')
  const blob = new Blob([`\uFEFF${header}${body}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'bababoi-users.csv'
  link.click()
  URL.revokeObjectURL(url)
  Message.success('用户列表已导出')
}
</script>

<template>
  <div class="adm-page">
    <AdminPageHeader
      eyebrow="运营 · 用户"
      title="用户管理"
      description="查看账号规模、学习数据与登录状态；禁用会立即吊销该账号的所有会话。"
    >
      <template #actions>
        <button class="adm-btn adm-btn--outline" type="button" @click="exportUsers">
          <AppIcon name="download" :size="15" />
          导出
        </button>
      </template>
    </AdminPageHeader>

    <section class="adm-panel">
      <div class="adm-toolbar">
        <a-input v-model="keyword" class="adm-search" placeholder="搜索用户名或邮箱" allow-clear>
          <template #prefix><AppIcon name="search" :size="14" /></template>
        </a-input>
        <a-select v-model="status" class="adm-filter" aria-label="状态筛选">
          <a-option value="all">全部状态</a-option>
          <a-option value="active">正常</a-option>
          <a-option value="disabled">已禁用</a-option>
        </a-select>
        <span class="adm-toolbar__spacer" />
        <span class="adm-muted">共 {{ data.usersTotal }} 个账号</span>
      </div>

      <div v-if="filteredUsers.length" class="adm-table-wrap">
        <table class="adm-table">
          <thead>
            <tr>
              <th>用户</th>
              <th>状态</th>
              <th>错题 / 生成</th>
              <th>练习</th>
              <th>最近登录</th>
              <th>注册时间</th>
              <th />
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in filteredUsers" :key="user.id">
              <td>
                <div class="adm-user-cell">
                  <span class="adm-avatar">{{ user.username.slice(-2).toUpperCase() }}</span>
                  <div>
                    <div class="adm-table__primary">{{ user.username }}</div>
                    <div class="adm-table__sub">{{ user.email }}</div>
                  </div>
                </div>
              </td>
              <td><StatusTag :tone="user.status === 'active' ? 'success' : 'neutral'" :label="user.status === 'active' ? '正常' : '已禁用'" /></td>
              <td class="adm-mono">{{ user.questions }} / {{ user.generated }}</td>
              <td class="adm-mono">{{ user.practice }}</td>
              <td class="adm-mono">{{ user.lastLogin }}</td>
              <td class="adm-mono">{{ user.createdAt }}</td>
              <td class="adm-table__right">
                <button class="adm-btn adm-btn--quiet adm-btn--sm" type="button" @click="openUser(user)">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="adm-empty">
        <strong>没有匹配的用户</strong>
        <p>换一个关键词，或清空筛选条件。</p>
      </div>
    </section>

    <a-drawer v-model:visible="drawerVisible" width="min(440px, 100vw)" :footer="false" title="用户详情">
      <div v-if="detailLoading" class="adm-empty">
        <strong>正在加载用户详情</strong>
        <p>GET /admin/users/{id}</p>
      </div>
      <template v-else-if="detail">
        <div class="adm-user-cell">
          <span class="adm-avatar adm-avatar--lg">{{ detail.username.slice(-2).toUpperCase() }}</span>
          <div>
            <div class="adm-table__primary">{{ detail.username }}</div>
            <div class="adm-table__sub">{{ detail.email }}</div>
          </div>
          <StatusTag
            class="adm-toolbar__spacer"
            :tone="detail.status === 'active' ? 'success' : 'neutral'"
            :label="detail.status === 'active' ? '正常' : '已禁用'"
          />
        </div>

        <div class="adm-detail-grid" style="margin-top: 18px">
          <dl class="adm-detail-item">
            <dt>用户 ID</dt>
            <dd class="adm-mono">#{{ detail.id }}</dd>
          </dl>
          <dl class="adm-detail-item">
            <dt>账号角色</dt>
            <dd>{{ detail.role === 'admin' ? '管理员' : '学生' }}</dd>
          </dl>
          <dl class="adm-detail-item">
            <dt>错题 / 生成题</dt>
            <dd class="adm-mono">{{ detail.questions }} / {{ detail.generated }}</dd>
          </dl>
          <dl class="adm-detail-item">
            <dt>练习记录</dt>
            <dd class="adm-mono">{{ detail.practice }}</dd>
          </dl>
          <dl class="adm-detail-item">
            <dt>最近登录</dt>
            <dd class="adm-mono">{{ detail.lastLogin }}</dd>
          </dl>
          <dl class="adm-detail-item">
            <dt>注册时间</dt>
            <dd class="adm-mono">{{ detail.createdAt }}</dd>
          </dl>
        </div>

        <div v-if="detail.disabledReason" class="adm-warning-box" style="margin-top: 14px">
          <AppIcon name="warning" :size="15" />
          <span>禁用原因：{{ detail.disabledReason }}（{{ detail.disabledAt ?? '—' }}）</span>
        </div>

        <div class="adm-detail-section">
          <h3>个人 AI Key</h3>
          <div class="adm-detail-copy">
            <template v-if="detail.hasPersonalKey">
              已配置 {{ detail.provider ?? '—' }} · {{ detail.model ?? '—' }} · 尾号 {{ detail.keyLast4 ?? '—' }}。前端不回显完整 Key。
            </template>
            <template v-else>未配置个人 Key，使用系统默认 Key。</template>
          </div>
        </div>

        <div class="adm-detail-section">
          <h3>最近任务</h3>
          <ul v-if="detail.recentTasks?.length" class="adm-task-list">
            <li v-for="task in detail.recentTasks ?? []" :key="task.id">
              <span class="adm-task-list__title">{{ task.question }}</span>
              <StatusTag
                :tone="task.status === 'failed' ? 'danger' : task.status === 'running' ? 'running' : task.status === 'done' ? 'success' : 'neutral'"
                :label="task.status === 'failed' ? '失败' : task.status === 'running' ? '生成中' : task.status === 'done' ? '完成' : task.status === 'canceled' ? '已取消' : '排队'"
              />
              <span class="adm-task-list__meta">{{ task.code }} · {{ task.createdAt }}</span>
            </li>
          </ul>
          <div v-else class="adm-muted">该账号暂无任务记录。</div>
        </div>

        <div class="adm-detail-section">
          <h3>最近密码申请</h3>
          <ul v-if="detail.passwordRequests?.length" class="adm-task-list">
            <li v-for="request in detail.passwordRequests ?? []" :key="request.id">
              <span class="adm-task-list__title">{{ request.reason }}</span>
              <StatusTag
                :tone="request.status === 'pending' ? 'warning' : request.status === 'approved' ? 'success' : 'danger'"
                :label="request.status === 'pending' ? '待审批' : request.status === 'approved' ? '已通过' : '已拒绝'"
              />
              <span class="adm-task-list__meta">{{ request.submittedAt }}</span>
            </li>
          </ul>
          <p v-if="detail.pendingPasswordRequests" class="adm-muted" style="margin-top: 10px">
            该账号有 {{ detail.pendingPasswordRequests }} 个待处理密码申请。
            <RouterLink class="adm-link" to="/password-requests">前往审批 →</RouterLink>
          </p>
          <div v-else-if="!detail.passwordRequests?.length" class="adm-muted">该账号暂无密码申请。</div>
        </div>

        <div class="adm-detail-section">
          <h3>账号操作</h3>
          <div class="adm-modal-actions" style="justify-content: flex-start">
            <button
              class="adm-btn"
              :class="detail.status === 'active' ? 'adm-btn--danger' : 'adm-btn--outline'"
              type="button"
              @click="askAction(detail, detail.status === 'active' ? 'disable' : 'enable')"
            >
              {{ detail.status === 'active' ? '禁用账号' : '启用账号' }}
            </button>
            <button class="adm-btn adm-btn--outline" type="button" @click="askAction(detail, 'force-logout')">强制下线</button>
          </div>
          <p class="adm-muted" style="margin-top: 10px">
            密码重置不在此页直接操作；请在「密码申请」中审批学生的线上申请。
          </p>
        </div>
      </template>
    </a-drawer>

    <a-modal v-model:visible="actionVisible" :title="actionTitle" :footer="false" :width="440">
      <div v-if="actionUser" class="adm-approval">
        <div class="adm-approval__user">
          <span class="adm-avatar adm-avatar--lg">{{ actionUser.username.slice(-2).toUpperCase() }}</span>
          <div>
            <strong>{{ actionUser.username }}</strong>
            <span>{{ actionUser.email }}</span>
          </div>
        </div>

        <div v-if="actionKind === 'disable'" class="adm-field">
          <label for="user-action-reason">禁用原因（必填，至少 4 个字）</label>
          <a-textarea
            id="user-action-reason"
            v-model="actionReason"
            placeholder="例如：账号异常登录，临时禁用并联系本人。"
            :auto-size="{ minRows: 3, maxRows: 5 }"
          />
        </div>
        <div v-else-if="actionKind === 'enable'" class="adm-info-box">
          <AppIcon name="shield" :size="15" />
          <span>启用后旧会话不会恢复，该账号需要重新登录。</span>
        </div>
        <div v-else class="adm-warning-box">
          <AppIcon name="warning" :size="15" />
          <span>强制下线会递增 token_version，该账号所有设备上的会话立即失效。</span>
        </div>

        <div class="adm-modal-actions">
          <button class="adm-btn adm-btn--outline" type="button" @click="actionVisible = false">取消</button>
          <button
            class="adm-btn"
            :class="actionKind === 'disable' || actionKind === 'force-logout' ? 'adm-btn--danger' : 'adm-btn--primary'"
            type="button"
            :disabled="actionBusy"
            @click="confirmAction"
          >
            {{ actionBusy ? '正在提交…' : '确认' }}
          </button>
        </div>
      </div>
    </a-modal>
  </div>
</template>
