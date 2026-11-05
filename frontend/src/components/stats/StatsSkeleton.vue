<template>
  <div class="stats-skeleton" role="status" aria-live="polite" aria-label="正在加载统计数据">
    <span class="sr-only">正在加载统计数据…</span>

    <div class="stats-skeleton__kpis">
      <div v-for="index in 4" :key="index" class="sk-card">
        <span class="sk sk--label"></span>
        <span class="sk sk--value"></span>
        <span class="sk sk--hint"></span>
      </div>
    </div>

    <div class="stats-skeleton__panels">
      <div class="sk-panel">
        <span class="sk sk--title"></span>
        <span v-for="index in 4" :key="index" class="sk sk--row"></span>
      </div>

      <div class="sk-panel">
        <span class="sk sk--title"></span>
        <span class="sk sk--bar"></span>
        <span v-for="index in 3" :key="index" class="sk sk--row"></span>
      </div>
    </div>

    <div class="sk-panel">
      <span class="sk sk--title"></span>
      <span class="sk sk--chart"></span>
    </div>
  </div>
</template>

<style scoped>
.stats-skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.stats-skeleton__kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
}

.stats-skeleton__panels {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
  gap: var(--space-4);
}

.sk-card,
.sk-panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.sk-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-height: 136px;
  padding: var(--space-5);
}

.sk-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-6);
}

.sk {
  display: block;
  height: 12px;
  border-radius: var(--radius-sm);
  background: var(--color-page-deep);
  animation: stats-skeleton-pulse 1.8s ease-in-out infinite;
}

.sk--label {
  width: 68px;
  height: 14px;
}

.sk--value {
  width: 96px;
  height: 30px;
}

.sk--hint {
  width: 62%;
  margin-top: auto;
}

.sk--title {
  width: 120px;
  height: 18px;
}

.sk--row {
  width: 100%;
  height: 16px;
}

.sk-panel .sk--row:nth-of-type(3) {
  width: 82%;
}

.sk-panel .sk--row:nth-of-type(4) {
  width: 64%;
}

.sk--bar {
  width: 100%;
  height: 10px;
  margin-top: var(--space-2);
}

.sk--chart {
  width: 100%;
  height: 150px;
  margin-top: var(--space-2);
}

.sk:nth-child(2) {
  animation-delay: 0.15s;
}

.sk:nth-child(3) {
  animation-delay: 0.3s;
}

.sk:nth-child(4) {
  animation-delay: 0.45s;
}

@keyframes stats-skeleton-pulse {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.45;
  }
}

@media (max-width: 1023px) {
  .stats-skeleton__kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stats-skeleton__panels {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .stats-skeleton__kpis {
    gap: var(--space-3);
  }

  .sk-card {
    min-height: 124px;
    padding: var(--space-4);
  }

  .sk-panel {
    padding: var(--space-4);
  }
}
</style>
