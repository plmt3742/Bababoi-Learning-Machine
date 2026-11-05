<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="not-found-view">
    <a-result status="404" title="页面不存在" subtitle="你访问的地址可能已移动或删除。">
      <template #extra>
        <RouterLink to="/">
          <a-button type="primary">返回首页</a-button>
        </RouterLink>
      </template>
    </a-result>
  </div>
</template>

<style scoped>
.not-found-view {
  display: grid;
  min-height: 60vh;
  place-items: center;
  padding: var(--space-6) 0;
}
</style>
