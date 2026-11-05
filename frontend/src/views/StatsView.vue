<script setup lang="ts">
import PlaceholderPanel from '../components/common/PlaceholderPanel.vue'
import PageHeader from '../components/common/PageHeader.vue'
</script>

<template>
  <div class="page">
    <PageHeader eyebrow="Stats" title="统计" description="查看薄弱知识点与练习趋势。" />
    <PlaceholderPanel
      hint="后续在这里展示掌握度趋势、薄弱知识点排行与练习量统计；统计将在后续提供。"
      task="FE-014 · 统计"
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
