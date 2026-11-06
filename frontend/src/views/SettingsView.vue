<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  IconDown,
  IconEye,
  IconEyeInvisible,
  IconLock,
  IconPoweroff,
} from '@arco-design/web-vue/es/icon'
import PageHeader from '../components/common/PageHeader.vue'
import { deleteAiSettings, getAiSettings, saveAiSettings } from '../api/settings'
import { normalizeApiError } from '../api/errors'
import { useAuthStore } from '../stores/auth'
import type { AiProvider, AiSettings } from '../api/types'
import {
  DEFAULT_AI_MODEL,
  emptyAiSettingsErrors,
  formatSettingsTime,
  hasAiSettingsErrors,
  toAiSettingsUpdate,
  validateAiSettingsInput,
} from '../utils/settings'
import type { AiSettingsField } from '../utils/settings'

const FIELD_IDS: Record<AiSettingsField, string> = {
  provider: 'settings-provider',
  model: 'settings-model',
  base_url: 'settings-base-url',
  api_key: 'settings-api-key',
}

const FIELD_ORDER: AiSettingsField[] = ['provider', 'model', 'base_url', 'api_key']

const router = useRouter()
const auth = useAuthStore()

const settings = ref<AiSettings | null>(null)
const loading = ref(true)
const loadError = ref('')
const loadErrorCode = ref('')
const saving = ref(false)
const deleting = ref(false)
const showKey = ref(false)
const confirmDelete = ref(false)
const feedback = ref<{ tone: 'success' | 'danger'; text: string } | null>(null)
const errors = reactive(emptyAiSettingsErrors())
const form = reactive<{
  provider: AiProvider
  baseUrl: string
  model: string
  apiKey: string
}>({
  provider: 'deepseek',
  baseUrl: '',
  model: DEFAULT_AI_MODEL,
  apiKey: '',
})

const deleteCancelRef = ref<HTMLButtonElement | null>(null)
const deleteTriggerRef = ref<HTMLButtonElement | null>(null)

const user = computed(() => auth.user)
const accountRole = computed(() => (user.value ? '学习账号' : '—'))
const accountStatus = computed(() => (auth.isAuthenticated ? '已登录' : '未登录'))
const accountCreatedText = computed(() => formatSettingsTime(user.value?.created_at ?? null))
const configured = computed(() => settings.value?.configured === true)
const maskedKey = computed(() => settings.value?.api_key_masked ?? '')
const updatedText = computed(() => formatSettingsTime(settings.value?.updated_at ?? null))

const aiMeta = computed(() => {
  const current = settings.value
  if (!current?.configured) return ''

  const parts = [providerLabel(current.provider), current.model]
  if (current.base_url) parts.push(current.base_url)
  if (updatedText.value) parts.push(`更新于 ${updatedText.value}`)
  return parts.join(' · ')
})

function providerLabel(provider: AiProvider): string {
  return provider === 'openai_compatible' ? 'OpenAI 兼容' : 'DeepSeek'
}

function unconfiguredSettings(): AiSettings {
  return {
    configured: false,
    provider: 'deepseek',
    base_url: null,
    model: DEFAULT_AI_MODEL,
    api_key_masked: null,
    updated_at: null,
  }
}

function applySettings(next: AiSettings): void {
  settings.value = next
  form.provider = next.provider
  form.baseUrl = next.base_url ?? ''
  form.model = next.model || DEFAULT_AI_MODEL
  form.apiKey = ''
  showKey.value = false
  confirmDelete.value = false
  Object.assign(errors, emptyAiSettingsErrors())
}

function clearFieldError(field: AiSettingsField): void {
  errors[field] = ''
}

function handleProviderChange(): void {
  clearFieldError('provider')
}

function clearFormErrors(): void {
  Object.assign(errors, emptyAiSettingsErrors())
}

function focusFirstError(): void {
  const field = FIELD_ORDER.find((item) => errors[item])
  if (!field) return
  document.getElementById(FIELD_IDS[field])?.focus()
}

function errorText(cause: unknown): string {
  const apiError = normalizeApiError(cause)
  return apiError.code ? `${apiError.message}（${apiError.code}）` : apiError.message
}

async function loadSettings(): Promise<void> {
  loading.value = true
  loadError.value = ''
  loadErrorCode.value = ''
  feedback.value = null

  try {
    applySettings(await getAiSettings())
  } catch (cause) {
    const apiError = normalizeApiError(cause)
    settings.value = null
    loadError.value = apiError.message
    loadErrorCode.value = apiError.code
  } finally {
    loading.value = false
  }
}

function retryLoad(): void {
  if (loading.value) return
  void loadSettings()
}

async function handleSave(): Promise<void> {
  if (saving.value || deleting.value || loading.value || loadError.value) return

  feedback.value = null
  clearFormErrors()

  const input = {
    provider: form.provider,
    base_url: form.baseUrl,
    model: form.model,
    api_key: form.apiKey,
  }
  Object.assign(errors, validateAiSettingsInput(input))

  if (hasAiSettingsErrors(errors)) {
    await nextTick()
    focusFirstError()
    return
  }

  saving.value = true

  try {
    const saved = await saveAiSettings(toAiSettingsUpdate(input))
    applySettings(saved)
    feedback.value = {
      tone: 'success',
      text: '个人 API Key 已保存；输入框已清空，前端只保留服务端返回的脱敏值。',
    }
  } catch (cause) {
    feedback.value = { tone: 'danger', text: errorText(cause) }
  } finally {
    saving.value = false
  }
}

function requestDelete(): void {
  if (!configured.value || saving.value || deleting.value) return

  feedback.value = null
  confirmDelete.value = true
  void nextTick(() => deleteCancelRef.value?.focus())
}

function cancelDelete(): void {
  if (deleting.value) return

  confirmDelete.value = false
  void nextTick(() => deleteTriggerRef.value?.focus())
}

async function handleDelete(): Promise<void> {
  if (deleting.value) return

  deleting.value = true
  feedback.value = null

  try {
    await deleteAiSettings()
    applySettings(unconfiguredSettings())
    feedback.value = {
      tone: 'success',
      text: '已清除个人 Key；后续 AI 调用将使用系统默认 Key。',
    }
    await nextTick()
    document.getElementById(FIELD_IDS.api_key)?.focus()
  } catch (cause) {
    feedback.value = { tone: 'danger', text: errorText(cause) }
    confirmDelete.value = false
    await nextTick()
    deleteTriggerRef.value?.focus()
  } finally {
    deleting.value = false
  }
}

function handleLogout(): void {
  auth.logout()
  void router.push('/login')
}

onMounted(() => {
  void loadSettings()
})

onBeforeUnmount(() => {
  form.apiKey = ''
  showKey.value = false
})
</script>

<template>
  <div class="settings-view">
    <PageHeader
      eyebrow="Settings"
      title="个人设置"
      description="管理账号信息，并登记 AI 服务使用的个人 API Key。个人 Key 只提交到服务端，前端不保存完整值。"
    />

    <div class="settings-grid">
      <section class="panel account-panel" aria-labelledby="account-title">
        <header class="panel__head">
          <h2 id="account-title">账号信息</h2>
          <span class="panel__head-hint">Account</span>
        </header>

        <div class="panel__body account">
          <dl class="account__list">
            <div class="account__row">
              <dt>用户名</dt>
              <dd>{{ user?.username ?? '—' }}</dd>
            </div>
            <div class="account__row">
              <dt>用户 ID</dt>
              <dd class="account__mono">#{{ user?.id ?? '—' }}</dd>
            </div>
            <div v-if="user?.email" class="account__row">
              <dt>邮箱</dt>
              <dd>{{ user.email }}</dd>
            </div>
            <div class="account__row">
              <dt>账号类型</dt>
              <dd>{{ accountRole }}</dd>
            </div>
            <div class="account__row">
              <dt>账号状态</dt>
              <dd>
                <span class="tag tag--ok">
                  <span class="dot" aria-hidden="true"></span>
                  {{ accountStatus }}
                </span>
              </dd>
            </div>
            <div v-if="accountCreatedText" class="account__row">
              <dt>注册时间</dt>
              <dd>{{ accountCreatedText }}</dd>
            </div>
          </dl>

          <p class="hint account__note">账号信息由注册时确定，当前页面不支持修改用户名或密码。</p>

          <button
            class="btn btn--outline btn--sm account__logout"
            type="button"
            @click="handleLogout"
          >
            <IconPoweroff aria-hidden="true" />
            退出登录
          </button>
        </div>
      </section>

      <section class="panel ai-panel" aria-labelledby="ai-title">
        <header class="panel__head">
          <h2 id="ai-title">AI API 设置</h2>
          <span class="panel__head-hint">BYOK · P1</span>
        </header>

        <div class="panel__body ai">
          <div
            class="ai-status"
            :class="{ 'ai-status--configured': configured && !loading && !loadError }"
          >
            <span class="ai-status__dot" aria-hidden="true"></span>
            <div class="ai-status__main">
              <p class="ai-status__text" role="status" aria-live="polite">
                <template v-if="loading">正在读取当前设置…</template>
                <template v-else-if="loadError">设置读取失败</template>
                <template v-else-if="configured">
                  已配置个人 Key（<code class="ai-status__key">{{ maskedKey || '已保存' }}</code
                  >）
                </template>
                <template v-else>使用系统默认 Key</template>
              </p>
              <p v-if="!loading && configured && aiMeta" class="ai-status__meta">{{ aiMeta }}</p>
              <p v-else-if="!loading && !loadError" class="ai-status__meta">
                未配置个人 Key 时，由后端使用系统默认 Key。
              </p>
            </div>
            <span v-if="!loading && !loadError && configured" class="tag tag--ok ai-status__badge">
              个人 Key
            </span>
          </div>

          <div v-if="loading" class="ai-loading" role="status">
            <span class="ai-loading__spinner" aria-hidden="true"></span>
            正在读取 AI 设置…
          </div>

          <div v-else-if="loadError" class="settings-alert settings-alert--danger" role="alert">
            <span class="settings-alert__mark" aria-hidden="true"></span>
            <div class="settings-alert__body">
              <p>
                设置读取失败：{{ loadError }}
                <code v-if="loadErrorCode">（{{ loadErrorCode }}）</code>
              </p>
              <button class="btn btn--outline btn--sm" type="button" @click="retryLoad">
                重试
              </button>
            </div>
          </div>

          <template v-else>
            <div
              v-if="feedback"
              class="settings-alert"
              :class="
                feedback.tone === 'success' ? 'settings-alert--success' : 'settings-alert--danger'
              "
              :role="feedback.tone === 'danger' ? 'alert' : 'status'"
            >
              <span class="settings-alert__mark" aria-hidden="true"></span>
              <span>{{ feedback.text }}</span>
            </div>

            <form class="ai-form" novalidate @submit.prevent="handleSave">
              <div class="ai-form__row">
                <div class="field">
                  <label class="field-label" for="settings-provider">
                    API 提供方
                    <span class="req-text" aria-hidden="true">*</span>
                  </label>
                  <div class="select-wrap">
                    <select
                      id="settings-provider"
                      v-model="form.provider"
                      class="select"
                      required
                      :aria-invalid="errors.provider ? 'true' : 'false'"
                      :aria-describedby="errors.provider ? 'settings-provider-error' : undefined"
                      @change="handleProviderChange"
                    >
                      <option value="deepseek">DeepSeek</option>
                      <option value="openai_compatible">OpenAI 兼容</option>
                    </select>
                    <IconDown aria-hidden="true" />
                  </div>
                  <p v-if="errors.provider" id="settings-provider-error" class="field-error">
                    {{ errors.provider }}
                  </p>
                </div>

                <div class="field">
                  <label class="field-label" for="settings-model">
                    模型
                    <span class="req-text" aria-hidden="true">*</span>
                  </label>
                  <input
                    id="settings-model"
                    v-model="form.model"
                    class="input"
                    type="text"
                    required
                    maxlength="80"
                    autocomplete="off"
                    placeholder="deepseek-flash"
                    :aria-invalid="errors.model ? 'true' : 'false'"
                    :aria-describedby="
                      errors.model
                        ? 'settings-model-hint settings-model-error'
                        : 'settings-model-hint'
                    "
                    @input="clearFieldError('model')"
                  />
                  <p id="settings-model-hint" class="hint ai-form__hint">
                    默认 deepseek-flash；OpenAI 兼容服务请填写对方要求的模型名。
                  </p>
                  <p v-if="errors.model" id="settings-model-error" class="field-error">
                    {{ errors.model }}
                  </p>
                </div>
              </div>

              <div class="field">
                <label class="field-label" for="settings-base-url">Base URL（可选）</label>
                <input
                  id="settings-base-url"
                  v-model="form.baseUrl"
                  class="input"
                  type="url"
                  inputmode="url"
                  autocomplete="off"
                  placeholder="https://api.deepseek.com"
                  :aria-invalid="errors.base_url ? 'true' : 'false'"
                  :aria-describedby="
                    errors.base_url
                      ? 'settings-base-url-hint settings-base-url-error'
                      : 'settings-base-url-hint'
                  "
                  @input="clearFieldError('base_url')"
                />
                <p id="settings-base-url-hint" class="hint ai-form__hint">
                  {{
                    form.provider === 'openai_compatible'
                      ? '留空使用服务方默认地址；如填写必须是完整的 https:// 地址。'
                      : 'DeepSeek 使用官方默认地址；此字段仅在 OpenAI 兼容模式下保存。'
                  }}
                </p>
                <p v-if="errors.base_url" id="settings-base-url-error" class="field-error">
                  {{ errors.base_url }}
                </p>
              </div>

              <div class="field">
                <label class="field-label" for="settings-api-key">
                  API Key
                  <span class="req-text" aria-hidden="true">*</span>
                </label>
                <div class="key-field" :class="{ 'key-field--invalid': errors.api_key }">
                  <input
                    id="settings-api-key"
                    v-model="form.apiKey"
                    class="input key-field__input"
                    :type="showKey ? 'text' : 'password'"
                    required
                    autocomplete="off"
                    autocapitalize="off"
                    spellcheck="false"
                    placeholder="粘贴你的 API Key（至少 8 个字符）"
                    :aria-invalid="errors.api_key ? 'true' : 'false'"
                    :aria-describedby="
                      errors.api_key
                        ? 'settings-api-key-hint settings-api-key-error'
                        : 'settings-api-key-hint'
                    "
                    @input="clearFieldError('api_key')"
                  />
                  <button
                    class="key-field__toggle"
                    type="button"
                    :aria-pressed="showKey"
                    :aria-label="showKey ? '隐藏 API Key' : '显示 API Key'"
                    @click="showKey = !showKey"
                  >
                    <IconEyeInvisible v-if="showKey" aria-hidden="true" />
                    <IconEye v-else aria-hidden="true" />
                  </button>
                </div>
                <p id="settings-api-key-hint" class="hint ai-form__hint">
                  {{
                    configured
                      ? '已配置个人 Key；更新设置时需要重新输入完整 Key。'
                      : '至少 8 个字符；保存成功后输入框立即清空。'
                  }}
                </p>
                <p v-if="errors.api_key" id="settings-api-key-error" class="field-error">
                  {{ errors.api_key }}
                </p>
              </div>

              <div class="ai-actions">
                <button
                  class="btn btn--primary"
                  type="submit"
                  :disabled="saving || deleting"
                  :aria-busy="saving"
                >
                  {{ saving ? '保存中…' : configured ? '更新个人 Key' : '保存个人 Key' }}
                </button>
                <button
                  v-if="configured"
                  ref="deleteTriggerRef"
                  class="btn btn--danger"
                  type="button"
                  :disabled="saving || deleting"
                  @click="requestDelete"
                >
                  清除个人 Key
                </button>
              </div>

              <div
                v-if="confirmDelete"
                class="ai-confirm"
                role="group"
                aria-labelledby="settings-delete-confirm-title"
                @keydown.esc="cancelDelete"
              >
                <p id="settings-delete-confirm-title" class="ai-confirm__text">
                  确认清除个人 Key？清除后将使用系统默认 Key，此操作不可撤销。
                </p>
                <div class="ai-confirm__actions">
                  <button
                    ref="deleteCancelRef"
                    class="btn btn--outline btn--sm"
                    type="button"
                    :disabled="deleting"
                    @click="cancelDelete"
                  >
                    取消
                  </button>
                  <button
                    class="btn btn--danger btn--sm"
                    type="button"
                    :disabled="deleting"
                    :aria-busy="deleting"
                    @click="handleDelete"
                  >
                    {{ deleting ? '清除中…' : '确认清除' }}
                  </button>
                </div>
              </div>
            </form>

            <div class="ai-note" role="note">
              <IconLock class="ai-note__icon" aria-hidden="true" />
              <div class="ai-note__body">
                <p class="ai-note__title">
                  密钥只提交到服务端，前端不保存、不回显完整值；生成时由后端使用。
                </p>
                <p class="ai-note__text">
                  服务端加密保存；保存成功后输入框会自动清空，页面只显示脱敏结果。请勿在公共设备保存个人
                  Key。
                </p>
                <p class="ai-note__text">
                  BYOK 属于 P1 能力，不在 11.29 演示主路径上；待后端接入后，AI 生成才会实际使用个人
                  Key，当前保存仅登记配置。
                </p>
              </div>
            </div>
          </template>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.settings-view {
  min-width: 0;
}

.settings-grid {
  display: grid;
  grid-template-columns: minmax(0, 320px) minmax(0, 1fr);
  align-items: start;
  gap: var(--space-5);
}

.settings-grid > * {
  min-width: 0;
}

.account__list {
  display: grid;
  gap: var(--space-3);
  margin: 0;
}

.account__row {
  display: grid;
  grid-template-columns: 80px minmax(0, 1fr);
  align-items: baseline;
  gap: var(--space-3);
}

.account__row dt {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.account__row dd {
  min-width: 0;
  margin: 0;
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  overflow-wrap: anywhere;
}

.account__mono {
  font-family: var(--font-mono);
}

.account__note {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.account__logout {
  width: 100%;
  margin-top: var(--space-4);
}

.ai-status {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface-subtle);
}

.ai-status--configured {
  border-color: var(--color-success-border);
}

.ai-status__dot {
  flex: none;
  width: 8px;
  height: 8px;
  margin-top: 7px;
  border-radius: 50%;
  background: var(--color-text-3);
}

.ai-status--configured .ai-status__dot {
  background: var(--color-success);
}

.ai-status__main {
  min-width: 0;
}

.ai-status__text {
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 600;
  overflow-wrap: anywhere;
}

.ai-status__key {
  padding: 1px 5px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 500;
}

.ai-status__meta {
  margin-top: 2px;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  overflow-wrap: anywhere;
}

.ai-status__badge {
  flex: none;
  margin-left: auto;
}

.ai-loading {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-5);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.ai-loading__spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--color-border-strong);
  border-right-color: var(--color-primary);
  border-radius: 50%;
  animation: settings-spin 0.7s linear infinite;
}

@keyframes settings-spin {
  to {
    transform: rotate(360deg);
  }
}

.settings-alert {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  margin-top: var(--space-4);
  padding: 10px var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.settings-alert--danger {
  border-color: var(--color-danger-border);
  background: var(--color-danger-soft);
  color: var(--color-danger-text);
}

.settings-alert--success {
  border-color: var(--color-success-border);
  background: var(--color-success-soft);
  color: var(--color-success-text);
}

.settings-alert__mark {
  flex: none;
  width: 6px;
  height: 6px;
  margin-top: 8px;
  background: currentColor;
}

.settings-alert__body {
  display: grid;
  justify-items: start;
  gap: var(--space-2);
  min-width: 0;
}

.ai-form {
  display: grid;
  gap: var(--space-4);
  margin-top: var(--space-5);
}

.ai-form__row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--space-4);
}

.field {
  min-width: 0;
}

.ai-form__hint {
  margin-top: 6px;
}

.key-field {
  position: relative;
  display: flex;
}

.key-field__input {
  padding-right: 46px;
}

.key-field--invalid .key-field__input {
  border-color: var(--color-danger);
}

.key-field__toggle {
  position: absolute;
  top: 4px;
  right: 4px;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-3);
}

.key-field__toggle:hover {
  background: var(--color-bg);
  color: var(--color-text-1);
}

.key-field__toggle svg {
  width: var(--icon-sm);
  height: var(--icon-sm);
}

.ai-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
  padding-top: var(--space-1);
}

.ai-confirm {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-danger-border);
  border-radius: var(--radius-md);
  background: var(--color-danger-soft);
}

.ai-confirm__text {
  color: var(--color-danger-text);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.ai-confirm__actions {
  display: flex;
  gap: var(--space-2);
}

.ai-note {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  margin-top: var(--space-5);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-primary-softer);
}

.ai-note__icon {
  flex: none;
  width: var(--icon-md);
  height: var(--icon-md);
  margin-top: 2px;
  color: var(--color-primary-active);
}

.ai-note__body {
  min-width: 0;
}

.ai-note__title {
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 600;
}

.ai-note__text {
  margin-top: 2px;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

@media (max-width: 900px) {
  .settings-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .settings-grid {
    gap: var(--space-4);
  }

  .account__row {
    grid-template-columns: 76px minmax(0, 1fr);
  }

  .ai-form__row {
    grid-template-columns: minmax(0, 1fr);
  }

  .ai-status {
    flex-wrap: wrap;
  }

  .ai-status__badge {
    margin-left: 0;
  }

  .ai-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .ai-actions .btn {
    width: 100%;
  }

  .ai-confirm {
    align-items: stretch;
    flex-direction: column;
  }

  .ai-confirm__actions {
    flex-direction: column;
  }

  .ai-confirm__actions .btn {
    width: 100%;
  }
}
</style>
