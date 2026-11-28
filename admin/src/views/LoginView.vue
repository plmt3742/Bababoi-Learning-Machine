<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppIcon from '../components/AppIcon.vue'
import { useAdminAuth } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAdminAuth()

const username = ref('')
const password = ref('')
const submitting = ref(false)
const error = ref('')

const demoUsername = import.meta.env.VITE_ADMIN_DEMO_USERNAME ?? ''
const demoPassword = import.meta.env.VITE_ADMIN_DEMO_PASSWORD ?? ''
const demoEnabled =
  import.meta.env.VITE_ADMIN_DEMO === 'true' && demoUsername.length > 0 && demoPassword.length > 0

function resolveRedirect(value: unknown): string {
  if (typeof value !== 'string') return '/'
  if (!value.startsWith('/') || value.startsWith('//') || value.startsWith('/\\')) return '/'
  return value
}

async function submit(): Promise<void> {
  if (submitting.value) return
  error.value = ''
  submitting.value = true
  try {
    await auth.login(username.value, password.value)
    await router.replace(resolveRedirect(route.query.redirect))
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '登录失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

async function enterDemo(): Promise<void> {
  username.value = demoUsername
  password.value = demoPassword
  await submit()
}
</script>

<template>
  <main class="adm-login">
    <section class="adm-login__card" aria-labelledby="admin-login-title">
      <div class="adm-login__brand">
        <span class="adm-brand__mark" aria-hidden="true">
          <span v-for="index in 9" :key="index" />
        </span>
        <span class="adm-login__brand-name">Bababoi</span>
        <span class="adm-login__brand-dot" aria-hidden="true">·</span>
        <span class="adm-login__brand-tagline">错题学习机</span>
        <span class="adm-login__admin-badge">Admin</span>
      </div>

      <header class="adm-login__head">
        <p class="adm-eyebrow">管理端</p>
        <h1 id="admin-login-title">登录内部运维台</h1>
        <p>监控 AI 质量、任务队列与审计记录。仅限授权管理员访问。</p>
      </header>

      <form class="adm-login__form" @submit.prevent="submit">
        <label class="adm-sr-only" for="admin-username">管理员用户名</label>
        <a-input
          id="admin-username"
          v-model="username"
          size="large"
          placeholder="管理员用户名"
          aria-label="管理员用户名"
          allow-clear
          autocomplete="username"
        >
          <template #prefix><AppIcon name="users" :size="15" /></template>
        </a-input>
        <label class="adm-sr-only" for="admin-password">管理员密码</label>
        <a-input-password
          id="admin-password"
          v-model="password"
          size="large"
          placeholder="密码"
          aria-label="管理员密码"
          allow-clear
          autocomplete="current-password"
        >
          <template #prefix><AppIcon name="key" :size="15" /></template>
        </a-input-password>

        <p v-if="error" class="adm-login__error" role="alert">{{ error }}</p>

        <button class="adm-btn adm-btn--primary adm-btn--block adm-login__submit" type="submit" :disabled="submitting">
          {{ submitting ? '正在验证…' : '进入管理端' }}
          <AppIcon v-if="!submitting" name="arrow" :size="15" />
        </button>
      </form>

      <div v-if="demoEnabled" class="adm-login__demo">
        <div>演示环境：使用 <strong>{{ demoUsername }}</strong> 登录，仅当 <code>VITE_ADMIN_DEMO=true</code> 时显示。</div>
        <button type="button" :disabled="submitting" @click="enterDemo">使用演示账号一键进入</button>
      </div>
      <p v-else class="adm-login__demo">管理员账号由服务端预置，请联系系统负责人开通或重置。</p>

      <p class="adm-login__footnote">内部运维台 · 独立会话 · 所有敏感操作写入审计</p>
    </section>
  </main>
</template>
