<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps<{
  activeCount: number | null
  failedCount: number | null
  draftState: 'present' | 'none' | 'unknown'
}>()

const activeText = computed(() => (props.activeCount === null ? '—' : String(props.activeCount)))
const failedText = computed(() => (props.failedCount === null ? '—' : String(props.failedCount)))
const draftText = computed(() => {
  if (props.draftState === 'present') return '有'
  if (props.draftState === 'none') return '无'
  return '—'
})

const activeLabel = computed(() =>
  props.activeCount === null
    ? '进行中任务状态暂不可用，查看任务中心'
    : `进行中任务 ${props.activeCount} 个，查看任务中心`,
)

const failedLabel = computed(() =>
  props.failedCount === null
    ? '失败任务状态暂不可用，查看任务中心'
    : `失败任务 ${props.failedCount} 个，查看任务中心`,
)

const draftLabel = computed(() => {
  if (props.draftState === 'unknown') return '草稿状态暂不可用，打开录入错题'
  return props.draftState === 'present' ? '有未完成草稿，继续编辑' : '没有未完成草稿，录入新错题'
})
</script>

<template>
  <section class="status-strip" aria-label="学习状态">
    <RouterLink class="status-strip__item" to="/tasks" :aria-label="activeLabel">
      <span class="status-strip__label">进行中任务</span>
      <span
        class="status-strip__value"
        :class="{ 'status-strip__value--muted': activeCount === null }"
      >
        {{ activeText }}
        <span v-if="activeCount !== null" class="status-strip__unit">个</span>
      </span>
      <svg
        class="status-strip__arrow"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="m9 6 6 6-6 6" />
      </svg>
    </RouterLink>

    <RouterLink class="status-strip__item" to="/tasks" :aria-label="failedLabel">
      <span class="status-strip__label">失败任务</span>
      <span
        class="status-strip__value"
        :class="{ 'status-strip__value--muted': failedCount === null }"
      >
        {{ failedText }}
        <span v-if="failedCount !== null" class="status-strip__unit">个</span>
      </span>
      <svg
        class="status-strip__arrow"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="m9 6 6 6-6 6" />
      </svg>
    </RouterLink>

    <RouterLink class="status-strip__item" to="/questions/new" :aria-label="draftLabel">
      <span class="status-strip__label">未完成草稿</span>
      <span
        class="status-strip__value"
        :class="{ 'status-strip__value--muted': draftState === 'unknown' }"
      >
        {{ draftText }}
      </span>
      <svg
        class="status-strip__arrow"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="m9 6 6 6-6 6" />
      </svg>
    </RouterLink>
  </section>
</template>

<style scoped>
.status-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.status-strip__item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-areas:
    'label arrow'
    'value arrow';
  align-items: center;
  gap: 1px var(--space-2);
  min-width: 0;
  padding: var(--space-4) var(--space-5);
  color: inherit;
  transition: background-color 0.15s ease;
}

.status-strip__item + .status-strip__item {
  border-left: 1px solid var(--color-border);
}

.status-strip__item:hover {
  background: var(--color-surface-hover);
  color: inherit;
}

.status-strip__label {
  grid-area: label;
  min-width: 0;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: 20px;
  font-weight: 500;
}

.status-strip__value {
  grid-area: value;
  color: var(--color-text-1);
  font-family: var(--font-mono);
  font-size: var(--text-lg);
  line-height: 24px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.status-strip__value--muted {
  color: var(--color-text-3);
}

.status-strip__unit {
  margin-left: 2px;
  color: var(--color-text-3);
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  font-weight: 400;
}

.status-strip__arrow {
  grid-area: arrow;
  width: 15px;
  height: 15px;
  color: var(--color-text-3);
  transition: transform 0.15s ease;
}

.status-strip__item:hover .status-strip__arrow {
  transform: translateX(2px);
}

@media (max-width: 767px) {
  .status-strip__item {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      'label'
      'value';
    gap: 0;
    padding: var(--space-3) var(--space-2);
  }

  .status-strip__arrow {
    display: none;
  }
}
</style>
