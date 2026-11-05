<script setup lang="ts">
import { useRoute } from 'vue-router'
import PlaceholderPanel from '../components/common/PlaceholderPanel.vue'
import PageHeader from '../components/common/PageHeader.vue'

const route = useRoute()
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="QDETAIL-01"
      title="错题详情"
      description="查看题目、AI 分析与三道同类题。"
    />
    <PlaceholderPanel
      :hint="`当前路由参数 id = ${String(route.params.id)}；后续在此展示题目、分析结果与生成题卡。`"
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
