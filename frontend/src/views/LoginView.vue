<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FieldRule, FormInstance } from '@arco-design/web-vue'
import { IconLock, IconUser } from '@arco-design/web-vue/es/icon'
import PageHeader from '../components/common/PageHeader.vue'
import { useAuthStore } from '../stores/auth'

type AuthMode = 'login' | 'register'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const activeKey = ref<AuthMode>('login')
const form = reactive({
  username: '',
  password: '',
})

const isRegister = computed(() => activeKey.value === 'register')
const submitLabel = computed(() => (isRegister.value ? '注册并登录' : '登录'))

const rules: Record<string, FieldRule[]> = {
  username: [
    { required: true, message: '请输入用户名' },
    { minLength: 3, maxLength: 32, message: '用户名为 3–32 个字符' },
    {
      match: /^[A-Za-z0-9_\u4e00-\u9fff]+$/,
      message: '仅支持字母、数字、下划线、中文',
    },
  ],
  password: [
    { required: true, message: '请输入密码' },
    { minLength: 8, maxLength: 128, message: '密码至少 8 位' },
  ],
}

/** Only same-origin absolute paths are allowed, so `?redirect=` cannot be an open redirect. */
function resolveRedirect(value: unknown): string {
  if (typeof value !== 'string') return '/'
  if (!value.startsWith('/') || value.startsWith('//') || value.startsWith('/\\')) return '/'
  return value
}

function handleTabChange(key: string | number): void {
  activeKey.value = key === 'register' ? 'register' : 'login'
  auth.clearError()
  formRef.value?.clearValidate()
}

async function handleSubmit(): Promise<void> {
  if (!formRef.value || auth.loading) return

  const validationErrors = await formRef.value.validate()
  if (validationErrors) return

  try {
    const payload = {
      username: form.username.trim(),
      password: form.password,
    }

    if (isRegister.value) await auth.register(payload)
    else await auth.login(payload)

    await router.replace(resolveRedirect(route.query.redirect))
  } catch {
    // The auth store normalizes the error; the inline alert renders auth.error.
  }
}
</script>

<template>
  <main class="login-view">
    <a-card class="login-view__card" :bordered="false">
      <div class="login-view__brand">
        <img class="login-view__mark" src="/favicon.svg" alt="" width="40" height="40" />
        <div class="login-view__wordmark">
          <span class="login-view__name">Bababoi</span>
          <span class="login-view__tagline">Learning Machine</span>
        </div>
      </div>

      <PageHeader
        eyebrow="AUTH-01"
        :title="isRegister ? '注册学习账号' : '登录学习账号'"
        :description="
          isRegister
            ? '创建账号后自动登录，错题、任务与练习记录会同步到你的账号。'
            : '登录后同步你的错题、任务与练习记录。'
        "
      />

      <a-tabs
        v-model:active-key="activeKey"
        class="login-view__tabs"
        type="line"
        size="large"
        @change="handleTabChange"
      >
        <a-tab-pane key="login" title="登录" />
        <a-tab-pane key="register" title="注册" />
      </a-tabs>

      <a-form
        ref="formRef"
        class="login-view__form"
        :model="form"
        :rules="rules"
        layout="vertical"
        @submit="handleSubmit"
      >
        <a-form-item field="username" label="用户名">
          <a-input
            v-model="form.username"
            placeholder="3–32 位，字母/数字/下划线/中文"
            :max-length="32"
            autocomplete="username"
            allow-clear
            @input="auth.clearError"
          >
            <template #prefix>
              <IconUser />
            </template>
          </a-input>
        </a-form-item>

        <a-form-item field="password" label="密码">
          <a-input-password
            v-model="form.password"
            placeholder="至少 8 位"
            :max-length="128"
            :autocomplete="isRegister ? 'new-password' : 'current-password'"
            allow-clear
            @input="auth.clearError"
          >
            <template #prefix>
              <IconLock />
            </template>
          </a-input-password>
        </a-form-item>

        <a-alert v-if="auth.error" class="login-view__error" type="error" :show-icon="true">
          {{ auth.error }}
        </a-alert>

        <a-button
          class="login-view__submit"
          type="primary"
          html-type="submit"
          size="large"
          long
          :loading="auth.loading"
          :disabled="auth.loading"
        >
          {{ submitLabel }}
        </a-button>
      </a-form>

      <div class="login-view__hint" role="note">
        <span class="login-view__hint-label">演示账号</span>
        <code class="login-view__hint-code">student01 / password123</code>
      </div>

      <p class="login-view__footnote">P0 演示环境 · 注册后自动登录</p>
    </a-card>
  </main>
</template>

<style scoped>
.login-view {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: var(--space-6) var(--space-4);
  background: var(--color-bg);
}

.login-view__card {
  width: 100%;
  max-width: var(--layout-auth-card-max);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
}

.login-view :deep(.arco-card-body) {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-7);
}

.login-view__brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.login-view__mark {
  border-radius: var(--radius-md);
}

.login-view__wordmark {
  display: flex;
  flex-direction: column;
}

.login-view__name {
  font-size: var(--text-lg);
  font-weight: 600;
  line-height: var(--text-lg-leading);
}

.login-view__tagline {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: 1.35;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.login-view__tabs :deep(.arco-tabs-nav) {
  margin-bottom: 0;
}

.login-view__tabs :deep(.arco-tabs-content) {
  display: none;
}

.login-view__form {
  display: flex;
  flex-direction: column;
}

.login-view__form :deep(.arco-form-item) {
  margin-bottom: var(--space-4);
}

.login-view__error {
  margin-bottom: var(--space-4);
}

.login-view__submit {
  margin-top: var(--space-1);
}

.login-view__hint {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-fill);
}

.login-view__hint-label {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.login-view__hint-code {
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

.login-view__footnote {
  color: var(--color-text-3);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
  text-align: center;
}

@media (max-width: 767px) {
  .login-view :deep(.arco-card-body) {
    gap: var(--space-3);
    padding: var(--space-5);
  }
}
</style>
