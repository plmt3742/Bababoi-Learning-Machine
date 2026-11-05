<script setup lang="ts">
defineProps<{
  label: string
  value: string
  hint?: string
}>()
</script>

<template>
  <article class="stat-card">
    <p class="stat-card__label">{{ label }}</p>
    <p class="stat-card__value" :class="{ 'stat-card__value--muted': value === '—' }">
      {{ value }}
    </p>
    <p v-if="hint" class="stat-card__hint">{{ hint }}</p>
  </article>
</template>

<style scoped>
.stat-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-height: 136px;
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.stat-card__label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 600;
}

.stat-card__label::before {
  content: '';
  width: 14px;
  height: 2px;
  flex: none;
  background: var(--color-primary);
}

.stat-card__value {
  margin-top: var(--space-1);
  color: var(--color-text-1);
  font-family: var(--font-mono);
  font-size: var(--text-2xl);
  line-height: var(--text-2xl-leading);
  font-weight: 600;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}

.stat-card__value--muted {
  color: var(--color-text-3);
}

.stat-card__hint {
  margin-top: auto;
  padding-top: var(--space-2);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: 20px;
}

@media (max-width: 767px) {
  .stat-card {
    min-height: 124px;
    padding: var(--space-4);
  }

  .stat-card__value {
    font-size: var(--text-xl);
    line-height: var(--text-xl-leading);
  }
}
</style>
