<script setup lang="ts">
import { computed } from 'vue'
import type { Analysis } from '../../api/types'
import MarkdownRenderer from '../common/MarkdownRenderer.vue'
import { difficultyColor, difficultyLabel } from '../../utils/question'

const props = withDefaults(
  defineProps<{
    analysis: Analysis | null
    pending?: boolean
    failed?: boolean
  }>(),
  {
    pending: false,
    failed: false,
  },
)

const difficultyTone = computed(() => difficultyColor(props.analysis?.difficulty))
const difficultyText = computed(() => difficultyLabel(props.analysis?.difficulty))
</script>

<template>
  <a-card class="analysis-card" :bordered="false">
    <header class="analysis-card__header">
      <h2 class="analysis-card__title">AI 分析</h2>
      <a-tag v-if="analysis" size="small" :color="difficultyTone">
        难度：{{ difficultyText }}
      </a-tag>
    </header>

    <a-alert v-if="pending" class="analysis-card__notice" type="info" :show-icon="true">
      AI 正在分析这道题，完成后会自动更新考点、错误原因与解题摘要。
    </a-alert>

    <a-alert v-else-if="failed" class="analysis-card__notice" type="warning" :show-icon="true">
      分析任务没有成功完成，可在 AI 生成进度卡中重试，或直接查看原题与答案。
    </a-alert>

    <a-empty v-else-if="!analysis" description="暂无分析结果" />

    <div v-else class="analysis-card__body">
      <dl class="analysis-card__meta">
        <div class="analysis-card__meta-item">
          <dt>考点类型</dt>
          <dd>{{ analysis.topic_type }}</dd>
        </div>
      </dl>

      <section class="analysis-card__section">
        <h3 class="analysis-card__label">知识点</h3>
        <div class="analysis-card__tags">
          <a-tag
            v-for="point in analysis.knowledge_points"
            :key="point"
            size="small"
            color="arcoblue"
          >
            {{ point }}
          </a-tag>
        </div>
      </section>

      <section class="analysis-card__section">
        <h3 class="analysis-card__label">错误原因</h3>
        <ul class="analysis-card__reasons">
          <li v-for="(reason, index) in analysis.error_reasons" :key="index">
            <MarkdownRenderer :content="reason" compact />
          </li>
        </ul>
      </section>

      <section v-if="analysis.solution_summary" class="analysis-card__section">
        <h3 class="analysis-card__label">解题摘要</h3>
        <MarkdownRenderer :content="analysis.solution_summary" compact />
      </section>
    </div>
  </a-card>
</template>

<style scoped>
.analysis-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.analysis-card :deep(.arco-card-body) {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-5);
}

.analysis-card__header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.analysis-card__title {
  font-size: var(--text-lg);
  line-height: var(--text-lg-leading);
}

.analysis-card__notice {
  align-items: flex-start;
}

.analysis-card__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.analysis-card__meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-3);
  margin: 0;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  background: var(--color-fill);
}

.analysis-card__meta-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.analysis-card__meta-item dt {
  color: var(--color-text-3);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
}

.analysis-card__meta-item dd {
  margin: 0;
  color: var(--color-text-1);
  font-size: var(--text-sm);
  font-weight: 500;
  line-height: var(--text-sm-leading);
}

.analysis-card__section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.analysis-card__label {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  font-weight: 600;
  line-height: var(--text-sm-leading);
}

.analysis-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.analysis-card__reasons {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding-left: var(--space-5);
  color: var(--color-text-1);
}

.analysis-card__reasons li::marker {
  color: var(--color-text-3);
}

@media (max-width: 767px) {
  .analysis-card :deep(.arco-card-body) {
    padding: var(--space-4);
  }
}
</style>
