<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'

import type { PasswordRequest } from '../types'
import { useAdminData } from '../stores/adminData'
import AppIcon from './AppIcon.vue'

const props = defineProps<{
  visible: boolean
  request: PasswordRequest | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  approved: [request: PasswordRequest]
}>()

const data = useAdminData()

const step = ref<'confirm' | 'result'>('confirm')
const verified = ref(false)
const reason = ref('')
const deliveryChannel = ref('wechat')
const tempPassword = ref('')
const expiresAt = ref('')
const copied = ref(false)
const error = ref('')
const submitting = ref(false)

const channelOptions = [
  { value: 'wechat', label: '微信群 / 私聊' },
  { value: 'phone', label: '电话' },
  { value: 'email', label: '邮箱' },
  { value: 'other', label: '其他渠道' },
]

const canApprove = computed(
  () => verified.value && reason.value.trim().length >= 4 && !submitting.value,
)

const emailMismatch = computed(() => props.request?.emailMatches === false)

function reset(): void {
  step.value = 'confirm'
  verified.value = false
  reason.value = ''
  deliveryChannel.value = 'wechat'
  tempPassword.value = ''
  expiresAt.value = ''
  copied.value = false
  error.value = ''
  submitting.value = false
}

watch(
  () => [props.visible, props.request?.id],
  () => {
    if (props.visible) reset()
  },
)

function close(): void {
  emit('update:visible', false)
}

async function approve(): Promise<void> {
  if (!props.request) return
  if (!verified.value) {
    error.value = '请先确认已核验账号信息。'
    return
  }
  if (reason.value.trim().length < 4) {
    error.value = '请填写至少 4 个字的审批原因。'
    return
  }
  submitting.value = true
  error.value = ''
  try {
    const result = await data.approvePasswordRequest(props.request.id, {
      reason: reason.value.trim(),
      verified: true,
      delivery_channel: deliveryChannel.value,
    })
    tempPassword.value = result.temporary_password
    expiresAt.value = result.expires_at
    step.value = 'result'
    emit('approved', result.request)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '审批失败，请稍后重试'
    Message.error(error.value)
  } finally {
    submitting.value = false
  }
}

async function copyPassword(): Promise<void> {
  try {
    await navigator.clipboard.writeText(tempPassword.value)
    copied.value = true
    window.setTimeout(() => {
      copied.value = false
    }, 1800)
  } catch {
    copied.value = false
  }
}
</script>

<template>
  <a-modal
    :visible="visible"
    title="审批密码申请"
    :footer="false"
    :mask-closable="false"
    :width="520"
    @cancel="close"
  >
    <div v-if="request" class="adm-approval">
      <template v-if="step === 'confirm'">
        <div class="adm-approval__user">
          <span class="adm-avatar adm-avatar--lg">{{ request.username.slice(0, 1).toUpperCase() }}</span>
          <div>
            <strong>{{ request.username }}</strong>
            <span>提交邮箱：{{ request.email || '未填写' }}</span>
            <span>注册邮箱：{{ request.registeredEmail || '未登记' }}</span>
          </div>
        </div>

        <div class="adm-detail-grid">
          <dl class="adm-detail-item">
            <dt>申请时间</dt>
            <dd>{{ request.submittedAt }}</dd>
          </dl>
          <dl class="adm-detail-item">
            <dt>申请 IP</dt>
            <dd class="adm-mono">{{ request.ip }}</dd>
          </dl>
          <dl class="adm-detail-item">
            <dt>账号状态</dt>
            <dd>{{ request.accountStatus === 'active' ? '正常' : request.accountStatus }}</dd>
          </dl>
          <dl class="adm-detail-item">
            <dt>邮箱核验</dt>
            <dd>{{ request.emailMatches ? '一致' : '不一致' }}</dd>
          </dl>
          <dl class="adm-detail-item">
            <dt>申请原因</dt>
            <dd>{{ request.reason }}</dd>
          </dl>
        </div>

        <div v-if="emailMismatch" class="adm-warning-box">
          <AppIcon name="warning" :size="15" />
          <span>提交邮箱与账号登记邮箱不一致，请通过其他渠道确认申请人身份后再审批。</span>
        </div>

        <div class="adm-warning-box">
          <AppIcon name="warning" :size="15" />
          <span>
            通过后旧密码与所有登录会话立即失效；系统生成一次性临时密码，有效期 24 小时，学生登录后必须修改密码。
          </span>
        </div>

        <a-checkbox v-model="verified">已核验用户名与注册邮箱，确认是本人申请</a-checkbox>

        <div class="adm-field">
          <label for="approval-channel">临时密码发送渠道</label>
          <a-select id="approval-channel" v-model="deliveryChannel">
            <a-option v-for="option in channelOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </a-option>
          </a-select>
        </div>

        <div class="adm-field">
          <label for="approval-reason">审批原因（必填）</label>
          <a-textarea
            id="approval-reason"
            v-model="reason"
            placeholder="例如：用户名与注册邮箱一致，已通过班级群确认本人申请。"
            :auto-size="{ minRows: 3, maxRows: 5 }"
          />
        </div>

        <p v-if="error" class="adm-login__error" role="alert">{{ error }}</p>

        <div class="adm-modal-actions">
          <button class="adm-btn adm-btn--outline" type="button" @click="close">取消</button>
          <button class="adm-btn adm-btn--primary" type="button" :disabled="!canApprove" @click="approve">
            <AppIcon name="check" :size="14" />
            {{ submitting ? '正在生成…' : '通过并生成临时密码' }}
          </button>
        </div>
      </template>

      <template v-else>
        <div class="adm-approval__result-head">
          <span class="adm-success-mark"><AppIcon name="check" :size="20" /></span>
          <div>
            <strong>已生成临时密码</strong>
            <span>请通过 {{ channelOptions.find((option) => option.value === deliveryChannel)?.label }} 告知 {{ request.username }}，关闭后无法再次查看。</span>
          </div>
        </div>

        <div class="adm-temp-password">
          <code>{{ tempPassword }}</code>
          <button class="adm-btn adm-btn--outline adm-btn--sm" type="button" @click="copyPassword">
            <AppIcon name="copy" :size="13" />
            {{ copied ? '已复制' : '复制' }}
          </button>
        </div>

        <div class="adm-info-box">
          <AppIcon name="clock" :size="15" />
          <span>有效期至 {{ expiresAt || '24 小时内' }}。学生用临时密码登录后，系统只允许改密/登出，改密成功后旧会话全部失效。</span>
        </div>

        <div class="adm-warning-box">
          <AppIcon name="shield" :size="15" />
          <span>本次审批已写入审计。临时密码不写日志、不写审计、不存数据库明文。</span>
        </div>

        <div class="adm-modal-actions">
          <button class="adm-btn adm-btn--primary" type="button" @click="close">
            我已记录，关闭
          </button>
        </div>
      </template>
    </div>
  </a-modal>
</template>
