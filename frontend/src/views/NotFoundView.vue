<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="not-found-view">
    <section class="paper not-found-view__card" aria-labelledby="not-found-title">
      <p class="kicker not-found-view__code">404</p>
      <h1 id="not-found-title">页面不存在</h1>
      <p class="not-found-view__description">你访问的地址可能已移动或删除。</p>
      <RouterLink class="btn btn--primary not-found-view__action" to="/"> 返回首页 </RouterLink>
    </section>
  </div>
</template>

<style scoped>
.not-found-view {
  display: grid;
  min-height: 60vh;
  place-items: center;
  padding: var(--space-6) 0;
}

.not-found-view__card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-3);
  width: 100%;
  max-width: 520px;
  padding: var(--space-7);
}

.not-found-view__code {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  letter-spacing: 0.18em;
}

.not-found-view h1 {
  font-size: var(--text-2xl);
  line-height: var(--text-2xl-leading);
  letter-spacing: -0.012em;
}

.not-found-view__description {
  color: var(--color-text-2);
  font-size: 15px;
  line-height: 24px;
  text-wrap: pretty;
}

.not-found-view__action {
  margin-top: var(--space-2);
}

@media (max-width: 767px) {
  .not-found-view {
    min-height: 50vh;
    padding: var(--space-4) 0;
  }

  .not-found-view__card {
    gap: var(--space-2);
    padding: var(--space-5);
  }

  .not-found-view h1 {
    font-size: var(--text-xl);
    line-height: var(--text-xl-leading);
  }

  .not-found-view__description {
    font-size: var(--text-sm);
    line-height: var(--text-sm-leading);
  }
}
</style>
