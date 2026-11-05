<script setup lang="ts">
import PlaceholderPanel from '../components/common/PlaceholderPanel.vue'
import PageHeader from '../components/common/PageHeader.vue'
</script>

<template>
  <div class="page">
    <PageHeader eyebrow="HOME-01" title="首页" description="快速了解掌握度概览与今日复习入口。" />
    <PlaceholderPanel
      hint="后续在这里展示掌握度概览、最近错题和待处理任务。"
      task="FE-014 · 概览与统计"
    />
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
</style>
