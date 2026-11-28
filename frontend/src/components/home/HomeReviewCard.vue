<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getDuePractice } from '../../api/practice'

const total = ref(0)
const loading = ref(true)

async function loadDue(): Promise<void> {
  try {
    const result = await getDuePractice({ limit: 6 })
    total.value = result.total
  } catch {
    total.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadDue()
})
</script>

<template>
  <RouterLink v-if="!loading && total > 0" class="home-review" to="/practice">
    <span class="tag tag--point">今日待复习</span>
    <span class="home-review__body">
      <strong class="home-review__title">{{ total }} 道题到期</strong>
      <span class="home-review__text">按掌握度与上次练习时间排序，去练习页开始混刷。</span>
    </span>
    <span class="home-review__go">开始混刷 →</span>
  </RouterLink>
</template>

<style scoped>
.home-review {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  color: inherit;
  transition: border-color 0.15s ease;
}

.home-review:hover {
  border-color: var(--color-border-strong);
  color: inherit;
}

.home-review__body {
  display: flex;
  flex: 1 1 280px;
  flex-direction: column;
  min-width: 0;
}

.home-review__title {
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 600;
}

.home-review__text {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.home-review__go {
  margin-left: auto;
  color: var(--color-primary-active);
  font-size: var(--text-sm);
  font-weight: 500;
}

.home-review:hover .home-review__go {
  color: var(--color-primary);
}

@media (max-width: 767px) {
  .home-review {
    align-items: flex-start;
  }

  .home-review__body {
    flex-basis: 100%;
  }

  .home-review__go {
    margin-left: 0;
  }
}
</style>
