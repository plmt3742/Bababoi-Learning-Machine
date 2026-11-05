<script setup lang="ts">
import PlaceholderPanel from '../components/common/PlaceholderPanel.vue'
import PageHeader from '../components/common/PageHeader.vue'
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="QEDIT-01"
      title="录入错题"
      description="用文本或图片记录错题，交给 AI 分析与出题。"
    />
    <PlaceholderPanel
      hint="后续在这里接入文本录入、图片裁剪与多题文本提取确认流程。"
      task="FE-007 / FE-016 · 录入"
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
