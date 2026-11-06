<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { Task, TaskStatus } from '../../api/types'
import HomeSectionNotice from './HomeSectionNotice.vue'
import { taskFailureMessage, taskStageLabel, taskStatusLabel } from '../../utils/task'
import { formatStatsTime } from '../../utils/stats'

withDefaults(
  defineProps<{
    tasks: Task[]
    errorText?: string
  }>(),
  { errorText: '' },
)

const emit = defineEmits<{ retry: [] }>()

function statusTagClass(status: TaskStatus): string {
  if (status === 'failed') return 'tag tag--fail'
  if (status === 'running') return 'tag tag--run'
  if (status === 'done') return 'tag tag--ok'
  return 'tag'
}
</script>

<template>
  <section class="panel" aria-labelledby="home-tasks-title">
    <header class="panel__head">
      <h2 id="home-tasks-title">需要关注的任务</h2>
      <RouterLink class="panel__head-link" to="/tasks">
        任务中心
        <svg
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
    </header>

    <HomeSectionNotice
      v-if="errorText"
      tone="error"
      :title="tasks.length > 0 ? '任务状态刷新失败' : '任务状态加载失败'"
      :message="errorText"
      action-label="重试"
      @action="emit('retry')"
    />

    <HomeSectionNotice
      v-else-if="tasks.length === 0"
      title="暂无进行中的任务"
      message="录入错题后，AI 分析与生题进度会显示在这里。"
      action-label="去录入错题"
      action-to="/questions/new"
    />

    <ul v-if="tasks.length > 0" class="task-list">
      <li
        v-for="task in tasks"
        :key="task.id"
        class="task-row"
        :class="{ 'task-row--failed': task.status === 'failed' }"
      >
        <div class="task-row__top">
          <RouterLink
            class="task-row__link"
            :to="`/questions/${task.question_id}`"
            :aria-label="`查看题目 ${task.question_id} 的任务`"
          >
            <span class="task-row__title">题目 #{{ task.question_id }}</span>
            <span class="task-row__stage">{{ taskStageLabel(task.stage) }}</span>
          </RouterLink>

          <span :class="statusTagClass(task.status)">
            <span v-if="task.status === 'running'" class="dot" aria-hidden="true" />
            {{ taskStatusLabel(task.status) }}
          </span>
        </div>

        <p class="task-row__meta">
          <span>任务 #{{ task.id }}</span>
          <span class="task-row__sep" aria-hidden="true">·</span>
          <time :datetime="task.created_at">{{ formatStatsTime(task.created_at) }}</time>
          <template v-if="typeof task.target_index === 'number'">
            <span class="task-row__sep" aria-hidden="true">·</span>
            <span>第 {{ task.target_index }} 段</span>
          </template>
        </p>

        <p v-if="task.status === 'failed'" class="task-row__error">
          <code v-if="task.error_code" class="task-row__code">{{ task.error_code }}</code>
          <span>{{ taskFailureMessage(task) }}</span>
        </p>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.panel__head-link {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-left: auto;
  color: var(--color-primary-active);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 500;
}

.panel__head-link:hover {
  color: var(--color-primary);
}

.panel__head-link svg {
  width: 14px;
  height: 14px;
}

.task-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.task-row {
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.task-row:last-child {
  border-bottom: 0;
}

.task-row:hover {
  background: var(--color-surface-hover);
}

.task-row--failed {
  background: var(--color-danger-soft);
}

.task-row--failed:hover {
  background: var(--color-danger-soft);
}

.task-row__top {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.task-row__link {
  display: inline-flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-2);
  min-width: 0;
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 600;
}

.task-row__link:hover {
  color: var(--color-primary-active);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.task-row__link:focus-visible {
  outline-offset: 2px;
}

.task-row__stage {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  font-weight: 400;
}

.task-row__top .tag {
  margin-left: auto;
}

.task-row__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 3px var(--space-2);
  margin-top: 2px;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: 20px;
}

.task-row__meta time {
  font-family: var(--font-mono);
}

.task-row__sep {
  color: var(--color-border-strong);
}

.task-row__error {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 3px var(--space-2);
  margin-top: var(--space-2);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  overflow-wrap: anywhere;
}

.task-row__code {
  color: var(--color-danger-text);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 600;
}

@media (max-width: 767px) {
  .task-row {
    padding: var(--space-3) var(--space-4);
  }

  .task-row__top .tag {
    margin-left: 0;
  }
}
</style>
