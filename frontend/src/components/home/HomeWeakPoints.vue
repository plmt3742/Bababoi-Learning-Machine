<script setup lang="ts">
import { computed } from 'vue'
import type { StatsWeakKnowledgePoint } from '../../api/types'
import WeakPointList from '../stats/WeakPointList.vue'
import HomeSectionNotice from './HomeSectionNotice.vue'

const props = withDefaults(
  defineProps<{
    points: StatsWeakKnowledgePoint[]
    errorText?: string
  }>(),
  { errorText: '' },
)

const emit = defineEmits<{ retry: [] }>()

const topPoints = computed(() => props.points.slice(0, 5))

const headHint = computed(() => {
  if (!props.errorText) return '按错误次数排序 · Top 5'
  if (topPoints.value.length > 0) return '刷新失败 · 显示上次结果'
  return '暂不可用'
})
</script>

<template>
  <section class="panel" aria-labelledby="home-weak-title">
    <header class="panel__head">
      <h2 id="home-weak-title">薄弱知识点</h2>
      <span class="panel__head-hint">{{ headHint }}</span>
    </header>

    <HomeSectionNotice
      v-if="errorText"
      tone="error"
      :title="topPoints.length > 0 ? '薄弱知识点刷新失败' : '薄弱知识点加载失败'"
      :message="errorText"
      action-label="重试"
      @action="emit('retry')"
    />

    <div v-if="topPoints.length > 0 || !errorText" class="weak-body">
      <WeakPointList :points="topPoints" />
    </div>
  </section>
</template>

<style scoped>
.panel__head-hint {
  margin-left: auto;
}

.weak-body {
  padding: 0;
}
</style>
