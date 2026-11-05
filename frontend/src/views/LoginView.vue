<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FieldRule, FormInstance } from '@arco-design/web-vue'
import { IconLock, IconUser } from '@arco-design/web-vue/es/icon'
import BrandMark from '../components/layout/BrandMark.vue'
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
    // The auth store normalizes the error; the inline error panel renders auth.error.
  }
}
</script>

<template>
  <main class="login-view">
    <section class="login-view__card" aria-labelledby="login-title">
      <div class="login-view__brand">
        <BrandMark />
        <span class="login-view__name">Bababoi</span>
        <span class="login-view__brand-dot" aria-hidden="true">·</span>
        <span class="login-view__tagline">错题学习机</span>
      </div>

      <header class="login-view__head">
        <p class="kicker">Account</p>
        <h1 id="login-title" class="login-view__title">
          {{ isRegister ? '注册学习账号' : '登录学习账号' }}
        </h1>
        <p class="login-view__description">
          {{
            isRegister
              ? '创建账号后自动登录，错题、任务与练习记录会同步到你的账号。'
              : '登录后同步你的错题、任务与练习记录。'
          }}
        </p>
      </header>

      <div class="login-view__switch" role="group" aria-label="登录或注册">
        <button
          type="button"
          class="login-view__switch-btn"
          :class="{ 'is-active': activeKey === 'login' }"
          :aria-pressed="activeKey === 'login'"
          @click="handleTabChange('login')"
        >
          登录
        </button>
        <button
          type="button"
          class="login-view__switch-btn"
          :class="{ 'is-active': activeKey === 'register' }"
          :aria-pressed="activeKey === 'register'"
          @click="handleTabChange('register')"
        >
          注册
        </button>
      </div>

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

        <div v-if="auth.error" class="login-view__error" role="alert">
          <span class="login-view__error-mark" aria-hidden="true"></span>
          <span>{{ auth.error }}</span>
        </div>

        <button
          class="btn btn--primary btn--block login-view__submit"
          type="submit"
          :disabled="auth.loading"
          :aria-busy="auth.loading"
        >
          <span v-if="auth.loading" class="login-view__spinner" aria-hidden="true"></span>
          {{ auth.loading ? '处理中…' : submitLabel }}
        </button>
      </a-form>

      <div class="login-view__hint" role="note">
        <span class="login-view__hint-label">演示账号</span>
        <code class="login-view__hint-code">student01 / password123</code>
      </div>

      <p class="login-view__footnote">演示环境 · 注册后自动登录</p>
    </section>
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
  padding: var(--space-7);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-frame);
  background: var(--color-surface);
  box-shadow: var(--shadow-frame);
}

.login-view__brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.login-view__name {
  color: var(--color-text-1);
  font-size: var(--text-lg);
  line-height: var(--text-lg-leading);
  font-weight: 650;
  letter-spacing: -0.01em;
}

.login-view__brand-dot {
  color: var(--color-border-strong);
}

.login-view__tagline {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.login-view__head {
  margin-top: var(--space-6);
}

.login-view__title {
  margin-top: 6px;
  font-size: var(--text-xl);
  line-height: var(--text-xl-leading);
  font-weight: 650;
  letter-spacing: -0.012em;
}

.login-view__description {
  margin-top: var(--space-2);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.login-view__switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px;
  margin-top: var(--space-5);
  padding: 3px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.login-view__switch-btn {
  min-height: 34px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  font-weight: 600;
  line-height: 1;
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease,
    color 0.15s ease;
}

.login-view__switch-btn:hover {
  color: var(--color-text-1);
}

.login-view__switch-btn.is-active {
  border-color: var(--color-border-strong);
  background: var(--color-surface);
  color: var(--color-text-1);
}

.login-view__form {
  margin-top: var(--space-5);
}

.login-view__form :deep(.arco-form-item) {
  margin-bottom: var(--space-4);
}

.login-view__error {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  padding: 10px var(--space-3);
  border: 1px solid var(--color-danger-border);
  border-radius: var(--radius-md);
  background: var(--color-danger-soft);
  color: var(--color-danger-text);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.login-view__error-mark {
  flex: none;
  width: 6px;
  height: 6px;
  margin-top: 8px;
  background: var(--color-danger);
}

.login-view__submit {
  margin-top: var(--space-1);
}

.login-view__spinner {
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: login-spin 0.7s linear infinite;
}

@keyframes login-spin {
  to {
    transform: rotate(360deg);
  }
}

.login-view__hint {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-5);
  padding: 10px var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
}

.login-view__hint-label {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.login-view__hint-code {
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.login-view__footnote {
  margin-top: var(--space-4);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-align: center;
}

@media (max-width: 767px) {
  .login-view {
    padding: var(--space-4) var(--space-3);
  }

  .login-view__card {
    padding: var(--space-5);
  }

  .login-view__head {
    margin-top: var(--space-5);
  }

  .login-view__form {
    margin-top: var(--space-4);
  }
}
</style>
