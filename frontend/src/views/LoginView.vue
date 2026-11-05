<script setup lang="ts">
import { RouterLink } from 'vue-router'
import PageHeader from '../components/common/PageHeader.vue'
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
        title="登录"
        description="登录后同步你的错题、任务与练习记录。"
      />

      <a-empty description="登录表单将在 FE-005 接入" />

      <RouterLink class="login-view__back" to="/">先浏览页面骨架 →</RouterLink>
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
  gap: var(--space-5);
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

.login-view__back {
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

@media (max-width: 767px) {
  .login-view :deep(.arco-card-body) {
    padding: var(--space-5);
  }
}
</style>
