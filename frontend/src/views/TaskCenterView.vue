<script setup lang="ts">
import PlaceholderPanel from '../components/common/PlaceholderPanel.vue'
import PageHeader from '../components/common/PageHeader.vue'
</script>

<template>
  <div class="page">
    <PageHeader eyebrow="TASK-01" title="任务中心" description="跟踪分析与生题任务，失败可重试。" />
    <PlaceholderPanel
      hint="后续在这里展示任务队列、阶段进度、失败原因与重试入口。"
      task="FE-019 · 任务中心"
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
