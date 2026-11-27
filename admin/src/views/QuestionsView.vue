<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'

import AdminPageHeader from '../components/AdminPageHeader.vue'
import AppIcon from '../components/AppIcon.vue'
import StatusTag from '../components/StatusTag.vue'
import { useAdminData } from '../stores/adminData'
import type { QuestionModerationPayload } from '../api/admin'
import type { AdminQuestion, AdminQuestionDetail } from '../types'

type StatusFilter = 'all' | 'active' | 'hidden' | 'flagged'
type ModerationAction = 'hide' | 'restore' | 'flag' | 'unflag'

const data = useAdminData()

const keyword = ref('')
const subject = ref('all')
const status = ref<StatusFilter>('all')
const drawerVisible = ref(false)
const detail = ref<AdminQuestionDetail | null>(null)
const detailLoading = ref(false)

const moderationVisible = ref(false)
const moderationTarget = ref<{ id: number; action: ModerationAction } | null>(null)
const moderationReason = ref('')
const moderationBusy = ref(false)

let filterTimer: number | undefined

const subjects = ['高等数学', '线性代数', '概率论与数理统计', '大学物理']

const filteredQuestions = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  return data.questions.filter((question) => {
    if (subject.value !== 'all' && question.subject !== subject.value) return false
    if (status.value === 'flagged' && !question.flagged) return false
    if (status.value === 'hidden' && question.status !== 'hidden') return false
    if (status.value === 'active' && question.status !== 'active') return false
    if (!query) return true
    return `${question.id} ${question.excerpt} ${question.username} ${question.subject}`
      .toLowerCase()
      .includes(query)
  })
})

const moderationNeedsReason = computed(
  () => moderationTarget.value?.action === 'hide' || moderationTarget.value?.action === 'flag',
)

const moderationTitle = computed(() => {
  switch (moderationTarget.value?.action) {
    case 'hide':
      return '隐藏内容'
    case 'restore':
      return '恢复展示'
    case 'flag':
      return '标记 bad output'
    case 'unflag':
      return '取消标记'
    default:
      return '内容操作'
  }
})

function errorText(cause: unknown): string {
  return cause instanceof Error ? cause.message : '操作失败，请稍后重试'
}

async function load(): Promise<void> {
  try {
    await data.loadQuestions({
      q: keyword.value.trim() || undefined,
      status: status.value === 'active' || status.value === 'hidden' ? status.value : 'all',
      flagged: status.value === 'flagged' ? true : undefined,
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

async function openQuestion(question: AdminQuestion): Promise<void> {
  drawerVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await data.loadQuestionDetail(question.id)
  } catch (cause) {
    Message.error(errorText(cause))
    drawerVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

function askModeration(question: AdminQuestion, action: ModerationAction): void {
  moderationTarget.value = { id: question.id, action }
  moderationReason.value = ''
  moderationVisible.value = true
}

async function confirmModeration(): Promise<void> {
  const target = moderationTarget.value
  if (!target) return
  if (moderationNeedsReason.value && moderationReason.value.trim().length < 4) {
    Message.error('请填写至少 4 个字的原因')
    return
  }
  moderationBusy.value = true
  try {
    let payload: QuestionModerationPayload
    if (target.action === 'hide') {
      payload = { hidden: true, reason: moderationReason.value.trim() }
    } else if (target.action === 'restore') {
      payload = { hidden: false }
    } else if (target.action === 'flag') {
      payload = { flagged: true, reason: moderationReason.value.trim() }
    } else {
      payload = { flagged: false }
    }
    await data.moderateQuestion(target.id, payload)
    Message.success(
      target.action === 'hide'
        ? '已隐藏，学生端不再可见'
        : target.action === 'restore'
          ? '已恢复展示'
          : target.action === 'flag'
            ? '已标记 bad output'
            : '已取消标记',
    )
    moderationVisible.value = false
    if (detail.value?.id === target.id) {
      detail.value = await data.loadQuestionDetail(target.id)
    }
  } catch (cause) {
    Message.error(errorText(cause))
  } finally {
    moderationBusy.value = false
  }
}
</script>

<template>
  <div class="adm-page">
    <AdminPageHeader
      eyebrow="运营 · 内容"
      title="内容管理"
      description="定位错题与生成题内容问题；支持隐藏、软删除与 bad output 标记，不做富文本编辑。"
    />

    <section class="adm-panel">
      <div class="adm-toolbar">
        <a-input v-model="keyword" class="adm-search" placeholder="搜索题干、用户、学科或题目 ID" allow-clear>
          <template #prefix><AppIcon name="search" :size="14" /></template>
        </a-input>
        <a-select v-model="subject" class="adm-filter" aria-label="学科筛选">
          <a-option value="all">全部学科</a-option>
          <a-option v-for="item in subjects" :key="item" :value="item">{{ item }}</a-option>
        </a-select>
        <a-select v-model="status" class="adm-filter" aria-label="内容状态筛选">
          <a-option value="all">全部状态</a-option>
          <a-option value="active">正常展示</a-option>
          <a-option value="hidden">已隐藏</a-option>
          <a-option value="flagged">已标记</a-option>
        </a-select>
        <span class="adm-toolbar__spacer" />
        <span class="adm-muted">共 {{ data.questionsTotal }} 条内容</span>
      </div>

      <div v-if="filteredQuestions.length" class="adm-table-wrap">
        <table class="adm-table">
          <thead>
            <tr>
              <th>题目</th>
              <th>用户</th>
              <th>学科 / 题型</th>
              <th>状态</th>
              <th>生成 / 练习</th>
              <th>创建时间</th>
              <th />
            </tr>
          </thead>
          <tbody>
            <tr v-for="question in filteredQuestions" :key="question.id">
              <td>
                <div class="adm-table__excerpt">{{ question.excerpt }}</div>
                <div class="adm-table__sub">
                  <span class="adm-mono">Q-{{ question.id }}</span>
                  <span v-if="question.flagReason"> · {{ question.flagReason }}</span>
                </div>
              </td>
              <td>{{ question.username }}</td>
              <td>
                <div>{{ question.subject }}</div>
                <div class="adm-table__sub">{{ question.type }}<span v-if="question.chapter"> · {{ question.chapter }}</span></div>
              </td>
              <td>
                <div style="display: flex; flex-wrap: wrap; gap: 4px">
                  <StatusTag :tone="question.status === 'active' ? 'success' : 'neutral'" :label="question.status === 'active' ? '展示中' : '已隐藏'" />
                  <StatusTag v-if="question.flagged" tone="warning" label="已标记" :dot="false" />
                </div>
              </td>
              <td class="adm-mono">{{ question.generated }} / {{ question.practice }}</td>
              <td class="adm-mono">{{ question.createdAt }}</td>
              <td class="adm-table__right">
                <button class="adm-btn adm-btn--quiet adm-btn--sm" type="button" @click="openQuestion(question)">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="adm-empty">
        <strong>没有匹配的内容</strong>
        <p>换一个关键词或筛选条件。</p>
      </div>
    </section>

    <a-drawer v-model:visible="drawerVisible" width="min(460px, 100vw)" :footer="false" title="内容详情">
      <div v-if="detailLoading" class="adm-empty">
        <strong>正在加载内容详情</strong>
        <p>GET /admin/questions/{id}</p>
      </div>
      <template v-else-if="detail">
        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap">
          <StatusTag :tone="detail.status === 'active' ? 'success' : 'neutral'" :label="detail.status === 'active' ? '展示中' : '已隐藏'" />
          <StatusTag v-if="detail.flagged" tone="warning" label="已标记 bad output" :dot="false" />
          <span class="adm-muted adm-mono">Q-{{ detail.id }}</span>
        </div>

        <div class="adm-detail-copy" style="margin-top: 14px; color: var(--adm-ink); font-size: 13px">
          {{ detail.contentMd || detail.excerpt }}
        </div>

        <div class="adm-detail-grid" style="margin-top: 14px">
          <dl class="adm-detail-item"><dt>用户</dt><dd>{{ detail.username }}</dd></dl>
          <dl class="adm-detail-item"><dt>学科 / 题型</dt><dd>{{ detail.subject }} · {{ detail.type }}</dd></dl>
          <dl class="adm-detail-item"><dt>生成题</dt><dd class="adm-mono">{{ detail.generated }}</dd></dl>
          <dl class="adm-detail-item"><dt>练习记录</dt><dd class="adm-mono">{{ detail.practice }}</dd></dl>
          <dl class="adm-detail-item"><dt>创建时间</dt><dd class="adm-mono">{{ detail.createdAt }}</dd></dl>
          <dl class="adm-detail-item"><dt>内容状态</dt><dd>{{ detail.status === 'active' ? '正常' : '已隐藏' }}</dd></dl>
          <dl class="adm-detail-item"><dt>来源</dt><dd>{{ detail.sourceType || '—' }}</dd></dl>
          <dl class="adm-detail-item"><dt>图片</dt><dd>{{ detail.hasImage ? (detail.imagePath ?? '有') : '无' }}</dd></dl>
        </div>

        <div class="adm-detail-section">
          <h3>AI 分析摘要</h3>
          <div class="adm-detail-copy" style="font-size: 12px">{{ detail.analysis || '—' }}</div>
        </div>

        <div v-if="detail.answerMd" class="adm-detail-section">
          <h3>答案</h3>
          <div class="adm-detail-copy" style="font-size: 12px">{{ detail.answerMd }}</div>
        </div>

        <div v-if="detail.explanationMd" class="adm-detail-section">
          <h3>解析</h3>
          <div class="adm-detail-copy" style="font-size: 12px">{{ detail.explanationMd }}</div>
        </div>

        <div v-if="detail.tags?.length" class="adm-detail-section">
          <h3>标签</h3>
          <div style="display: flex; flex-wrap: wrap; gap: 4px">
            <span v-for="tag in detail.tags ?? []" :key="tag" class="adm-tag adm-tag--neutral">{{ tag }}</span>
          </div>
        </div>

        <div v-if="detail.flagReason" class="adm-warning-box" style="margin-top: 14px">
          <AppIcon name="warning" :size="15" />
          <span>{{ detail.flagReason }}</span>
        </div>

        <div v-if="detail.generatedQuestions?.length" class="adm-detail-section">
          <h3>生成题（{{ detail.generatedQuestions?.length ?? 0 }}）</h3>
          <ul class="adm-task-list">
            <li v-for="generated in detail.generatedQuestions ?? []" :key="generated.id">
              <span class="adm-task-list__title">{{ generated.contentMd }}</span>
              <StatusTag
                :tone="generated.validationStatus === 'passed' ? 'success' : 'warning'"
                :label="generated.validationStatus || '未知'"
                :dot="false"
              />
              <span class="adm-task-list__meta">
                第 {{ generated.targetIndex }} 段 · {{ generated.difficulty }} · 得分 {{ generated.validationScore ?? '—' }}
              </span>
            </li>
          </ul>
        </div>

        <div v-if="detail.tasks?.length" class="adm-detail-section">
          <h3>相关任务</h3>
          <ul class="adm-task-list">
            <li v-for="task in detail.tasks ?? []" :key="task.id">
              <span class="adm-task-list__title">{{ task.code }} · {{ task.stage === 'analysis' ? '分析' : '生题' }}</span>
              <StatusTag
                :tone="task.status === 'failed' ? 'danger' : task.status === 'done' ? 'success' : task.status === 'running' ? 'running' : 'neutral'"
                :label="task.status"
                :dot="false"
              />
              <span class="adm-task-list__meta">{{ task.createdAt }} · {{ task.duration }}</span>
            </li>
          </ul>
        </div>

        <div v-if="detail.recentAudit?.length" class="adm-detail-section">
          <h3>最近审计</h3>
          <ul class="adm-timeline" style="padding-left: 22px">
            <li v-for="entry in detail.recentAudit ?? []" :key="entry.id">
              <span class="adm-timeline__dot" />
              <p class="adm-timeline__title">{{ entry.action }} · {{ entry.admin }}</p>
              <p class="adm-timeline__meta"><time>{{ entry.time }}</time><span>{{ entry.reason }}</span></p>
            </li>
          </ul>
        </div>

        <div class="adm-detail-section">
          <h3>操作</h3>
          <div class="adm-modal-actions" style="justify-content: flex-start">
            <button class="adm-btn adm-btn--outline" type="button" @click="askModeration(detail, detail.status === 'active' ? 'hide' : 'restore')">
              {{ detail.status === 'active' ? '隐藏内容' : '恢复展示' }}
            </button>
            <button class="adm-btn adm-btn--danger" type="button" @click="askModeration(detail, detail.flagged ? 'unflag' : 'flag')">
              {{ detail.flagged ? '取消标记' : '标记 bad output' }}
            </button>
          </div>
          <p class="adm-muted" style="margin-top: 10px">所有操作会写入审计日志；不做物理删除。</p>
        </div>
      </template>
    </a-drawer>

    <a-modal v-model:visible="moderationVisible" :title="moderationTitle" :footer="false" :width="440">
      <div class="adm-approval">
        <div v-if="moderationNeedsReason" class="adm-field">
          <label for="moderation-reason">{{ moderationTarget?.action === 'hide' ? '隐藏原因' : '标记原因' }}（必填，至少 4 个字）</label>
          <a-textarea
            id="moderation-reason"
            v-model="moderationReason"
            placeholder="例如：题干公式渲染异常，先隐藏等待修复。"
            :auto-size="{ minRows: 3, maxRows: 5 }"
          />
        </div>
        <div v-else class="adm-info-box">
          <AppIcon name="shield" :size="15" />
          <span>该操作会恢复内容状态或清除标记，并写入审计。</span>
        </div>
        <div class="adm-modal-actions">
          <button class="adm-btn adm-btn--outline" type="button" @click="moderationVisible = false">取消</button>
          <button
            class="adm-btn"
            :class="moderationTarget?.action === 'hide' || moderationTarget?.action === 'flag' ? 'adm-btn--danger' : 'adm-btn--primary'"
            type="button"
            :disabled="moderationBusy"
            @click="confirmModeration"
          >
            {{ moderationBusy ? '正在提交…' : '确认' }}
          </button>
        </div>
      </div>
    </a-modal>
  </div>
</template>
