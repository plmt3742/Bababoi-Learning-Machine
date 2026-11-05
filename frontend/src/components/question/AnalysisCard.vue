<script setup lang="ts">
import { computed } from 'vue'
import type { Analysis } from '../../api/types'
import MarkdownRenderer from '../common/MarkdownRenderer.vue'
import { difficultyLabel } from '../../utils/question'

const props = withDefaults(
  defineProps<{
    analysis: Analysis | null
    pending?: boolean
    failed?: boolean
    taskLabel?: string
  }>(),
  {
    pending: false,
    failed: false,
    taskLabel: '',
  },
)

const difficultyText = computed(() => difficultyLabel(props.analysis?.difficulty))
const knowledgePoints = computed(() => props.analysis?.knowledge_points ?? [])
</script>

<template>
  <section class="paper analysis-card" aria-labelledby="analysis-title">
    <div class="paper__head">
      <div class="paper__title-group">
        <span class="ai-badge" aria-hidden="true">AI</span>
        <h2 id="analysis-title">AI 分析</h2>
        <span v-if="analysis" class="tag tag--ok">
          <svg
            class="icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="m5 12 4 4L19 6" />
          </svg>
          分析完成
        </span>
        <span v-else-if="failed" class="tag tag--fail">
          <svg
            class="icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            aria-hidden="true"
          >
            <path d="m6 6 12 12M18 6 6 18" />
          </svg>
          分析失败
        </span>
        <span v-else-if="pending" class="tag tag--run">
          <span class="dot" aria-hidden="true" />
          分析中
        </span>
      </div>
      <span v-if="taskLabel" class="paper__meta">{{ taskLabel }}</span>
    </div>

    <div class="paper__body">
      <p v-if="pending" class="analysis-note">
        AI 正在分析这道题，完成后会自动更新考点、错误原因与解题摘要。
      </p>

      <p v-else-if="failed" class="analysis-note analysis-note--error">
        分析任务没有成功完成，请在右侧「处理进度」中重试，或直接查看原题与答案。
      </p>

      <p v-else-if="!analysis" class="analysis-note analysis-note--quiet">暂无分析结果。</p>

      <template v-else>
        <dl class="analysis-meta">
          <div>
            <dt>考点类型</dt>
            <dd>{{ analysis.topic_type || '—' }}</dd>
          </div>
          <div>
            <dt>难度</dt>
            <dd>{{ difficultyText }}</dd>
          </div>
          <div>
            <dt>知识点</dt>
            <dd v-if="knowledgePoints.length" class="point-tags">
              <span v-for="point in knowledgePoints" :key="point" class="tag tag--point">
                {{ point }}
              </span>
            </dd>
            <dd v-else>—</dd>
          </div>
        </dl>

        <div v-if="analysis.error_reasons.length" class="analysis-block">
          <h3>错误原因</h3>
          <ol class="reasons">
            <li v-for="(reason, index) in analysis.error_reasons" :key="index">
              <MarkdownRenderer :content="reason" compact />
            </li>
          </ol>
        </div>

        <div v-if="analysis.solution_summary" class="analysis-block">
          <h3>解题摘要</h3>
          <div class="solution">
            <MarkdownRenderer :content="analysis.solution_summary" />
          </div>
        </div>

        <p class="ai-foot">由 deepseek-flash 生成，并随错题保存；请结合教材推导核对。</p>
      </template>
    </div>
  </section>
</template>

<style scoped>
.analysis-card {
  min-width: 0;
}

.ai-badge {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  background: var(--color-primary-softer);
  color: var(--color-primary-active);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 650;
  line-height: 1;
}

.analysis-note {
  padding: 10px var(--space-3);
  border: 1px solid var(--color-primary-soft);
  border-radius: var(--radius-md);
  background: var(--color-primary-softer);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.analysis-note--error {
  border-color: var(--color-danger-border);
  background: var(--color-danger-soft);
}

.analysis-note--quiet {
  border-color: var(--color-border);
  background: var(--color-bg);
  color: var(--color-text-3);
}

.analysis-meta {
  display: grid;
  grid-template-columns: 0.9fr 0.7fr 1.4fr;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.analysis-meta > div {
  min-width: 0;
  padding: 12px 14px;
  border-left: 1px solid var(--color-border);
}

.analysis-meta > div:first-child {
  border-left: 0;
}

.analysis-meta dt {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.analysis-meta dd {
  margin-top: 2px;
  color: var(--color-text-1);
  font-size: 15px;
  line-height: 24px;
  font-weight: 500;
  overflow-wrap: anywhere;
}

.point-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 4px;
}

.analysis-block {
  margin-top: var(--space-5);
}

.analysis-block h3 {
  margin-bottom: 9px;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 650;
  letter-spacing: 0.02em;
}

.reasons {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin: 0;
  padding: 0;
  list-style: none;
  counter-reset: reason;
}

.reasons li {
  position: relative;
  padding-left: 27px;
  color: var(--color-text-2);
  font-size: 15px;
  line-height: 24px;
}

.reasons li::before {
  counter-increment: reason;
  content: counter(reason, decimal-leading-zero);
  position: absolute;
  top: 0;
  left: 0;
  color: var(--color-primary);
  font-family: var(--font-math);
  font-size: var(--text-sm);
  line-height: 24px;
}

.reasons :deep(.markdown-renderer) {
  color: var(--color-text-2);
  font-size: 15px;
  line-height: 24px;
}

.reasons :deep(.markdown-renderer p) {
  margin-bottom: 0;
}

.solution {
  padding: 12px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
  color: var(--color-text-2);
}

.solution :deep(.markdown-renderer) {
  color: var(--color-text-2);
  font-size: var(--text-base);
  line-height: var(--text-base-leading);
}

.ai-foot {
  margin-top: var(--space-5);
  padding-top: 11px;
  border-top: 1px solid var(--color-border);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

@media (max-width: 767px) {
  .analysis-card .paper__head {
    padding: 12px var(--space-4);
  }

  .analysis-card .paper__body {
    padding: var(--space-4);
  }

  .analysis-meta {
    grid-template-columns: minmax(0, 1fr);
  }

  .analysis-meta > div {
    border-left: 0;
    border-top: 1px solid var(--color-border);
  }

  .analysis-meta > div:first-child {
    border-top: 0;
  }
}
</style>
