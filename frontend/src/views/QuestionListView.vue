<script setup lang="ts">
import PlaceholderPanel from '../components/common/PlaceholderPanel.vue'
import PageHeader from '../components/common/PageHeader.vue'
</script>

<template>
  <div class="page">
    <PageHeader eyebrow="QLIST-01" title="错题本" description="浏览、筛选并管理已录入的错题。" />
    <PlaceholderPanel
      hint="后续在这里提供错题列表、学科/标签筛选、搜索与分页。"
      task="FE-008 · 列表 / 详情"
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
