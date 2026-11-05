<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { StatsWeakKnowledgePoint } from '../../api/types'
import { formatAccuracy } from '../../utils/stats'

defineProps<{
  points: StatsWeakKnowledgePoint[]
}>()

function rank(index: number): string {
  return String(index + 1).padStart(2, '0')
}
</script>

<template>
  <div class="weak">
    <template v-if="points.length">
      <div class="weak__head" aria-hidden="true">
        <span>知识点</span>
        <span>错误</span>
        <span>练习</span>
        <span class="weak__head-accuracy">正确率</span>
      </div>

      <ol class="weak__list">
        <li v-for="(point, index) in points" :key="point.name" class="weak__row">
          <RouterLink
            class="weak__name"
            :to="{ name: 'questions', query: { tag: point.name } }"
            :aria-label="`查看「${point.name}」相关错题`"
          >
            <span class="weak__rank">{{ rank(index) }}</span>
            <span class="weak__label">{{ point.name }}</span>
            <svg
              class="weak__arrow"
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

          <span class="tag tag--unmastered weak__wrong">错 {{ point.wrong_count }}</span>
          <span class="weak__total">练习 {{ point.total_count }}</span>
          <span class="weak__accuracy">
            {{ formatAccuracy(point.accuracy, point.total_count) }}
          </span>
        </li>
      </ol>
    </template>

    <div v-else class="weak__empty">
      <span class="weak__empty-icon" aria-hidden="true">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M12 3 3 7.5 12 12l9-4.5L12 3Z" />
          <path d="m3 12 9 4.5 9-4.5" />
          <path d="m3 16.5 9 4.5 9-4.5" />
        </svg>
      </span>
      <div>
        <p>暂无薄弱知识点</p>
        <span>完成练习后，这里会按错误次数列出需要复习的知识点。</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.weak__head,
.weak__row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 72px 72px 76px;
  align-items: center;
  gap: var(--space-3);
}

.weak__head {
  padding: 9px var(--space-6);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface-subtle);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  letter-spacing: 0.02em;
}

.weak__head-accuracy {
  text-align: right;
}

.weak__list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.weak__row {
  padding: var(--space-3) var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.weak__row:last-child {
  border-bottom: 0;
}

.weak__row:hover {
  background: var(--color-surface-hover);
}

.weak__name {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  color: var(--color-text-1);
  font-size: var(--text-base);
  line-height: 24px;
  font-weight: 600;
}

.weak__name:hover {
  color: var(--color-primary-active);
}

.weak__rank {
  flex: none;
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 400;
  letter-spacing: 0.02em;
}

.weak__label {
  min-width: 0;
  overflow-wrap: anywhere;
}

.weak__arrow {
  width: 14px;
  height: 14px;
  flex: none;
  color: var(--color-text-3);
  opacity: 0;
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}

.weak__name:hover .weak__arrow,
.weak__name:focus-visible .weak__arrow {
  opacity: 1;
  transform: translateX(2px);
}

.weak__wrong {
  justify-self: start;
}

.weak__total {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.weak__accuracy {
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.weak__empty {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-6);
}

.weak__empty-icon {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  flex: none;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text-3);
}

.weak__empty-icon svg {
  width: 20px;
  height: 20px;
}

.weak__empty p {
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 600;
}

.weak__empty span {
  display: block;
  max-width: 44ch;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

@media (max-width: 600px) {
  .weak__head {
    display: none;
  }

  .weak__row {
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-areas:
      'name wrong'
      'total accuracy';
    gap: var(--space-1) var(--space-3);
    padding: var(--space-3) var(--space-4);
  }

  .weak__name {
    grid-area: name;
    align-self: center;
    gap: var(--space-2);
  }

  .weak__wrong {
    grid-area: wrong;
    justify-self: end;
  }

  .weak__total {
    grid-area: total;
  }

  .weak__accuracy {
    grid-area: accuracy;
    justify-self: end;
  }

  .weak__arrow {
    display: none;
  }

  .weak__empty {
    padding: var(--space-4);
  }
}
</style>
