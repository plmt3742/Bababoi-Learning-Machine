<script setup lang="ts">
import { useRoute } from 'vue-router'
import PlaceholderPanel from '../components/common/PlaceholderPanel.vue'
import PageHeader from '../components/common/PageHeader.vue'

const route = useRoute()
</script>

<template>
  <div class="page">
    <PageHeader eyebrow="Practice" title="练习" description="逐题作答、查看解析并记录掌握情况。" />
    <PlaceholderPanel
      :hint="
        route.params.id
          ? `当前从错题 ${String(route.params.id)} 进入；后续在此提供作答、计时与结果反馈。`
          : '后续在这里提供练习入口、作答、计时与结果反馈。'
      "
      task="FE-013 · 练习页"
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
