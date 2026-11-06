<template>
  <div class="home-skeleton" role="status" aria-live="polite" aria-label="正在加载学习概览">
    <span class="sr-only">正在加载学习概览…</span>

    <div class="sk-strip">
      <div v-for="index in 3" :key="`strip-${index}`" class="sk-strip__cell">
        <span class="sk sk--label" />
        <span class="sk sk--value" />
      </div>
    </div>

    <div class="sk-kpis">
      <div v-for="index in 4" :key="`kpi-${index}`" class="sk-kpi">
        <span class="sk sk--label" />
        <span class="sk sk--number" />
        <span class="sk sk--hint" />
      </div>
    </div>

    <div class="sk-panels">
      <div v-for="index in 2" :key="`panel-${index}`" class="sk-panel">
        <span class="sk sk--title" />
        <span v-for="row in 4" :key="`row-${index}-${row}`" class="sk sk--row" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.sk {
  display: block;
  border-radius: var(--radius-sm);
  background: var(--color-page-deep);
  animation: home-skeleton-pulse 1.8s ease-in-out infinite;
}

.sk-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.sk-strip__cell {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4) var(--space-5);
}

.sk-strip__cell + .sk-strip__cell {
  border-left: 1px solid var(--color-border);
}

.sk--label {
  width: 42%;
  height: 14px;
}

.sk--value {
  width: 28%;
  height: 24px;
}

.sk-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
}

.sk-kpi {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-height: 136px;
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.sk--number {
  width: 48%;
  height: 28px;
  margin-top: var(--space-1);
}

.sk--hint {
  width: 68%;
  height: 14px;
  margin-top: auto;
}

.sk-panels {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
  align-items: start;
  gap: var(--space-4);
}

.sk-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.sk--title {
  width: 34%;
  height: 18px;
  margin-bottom: var(--space-1);
}

.sk--row {
  width: 100%;
  height: 44px;
}

.sk:nth-child(2) {
  animation-delay: 0.12s;
}

.sk:nth-child(3) {
  animation-delay: 0.24s;
}

@keyframes home-skeleton-pulse {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.45;
  }
}

@media (max-width: 1023px) {
  .sk-kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .sk-panels {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .home-skeleton {
    gap: var(--space-3);
  }

  .sk-strip__cell {
    padding: var(--space-3) var(--space-4);
  }

  .sk-kpis,
  .sk-panels {
    gap: var(--space-3);
  }

  .sk-kpi {
    min-height: 124px;
    padding: var(--space-4);
  }

  .sk-panel {
    padding: var(--space-4);
  }
}
</style>
