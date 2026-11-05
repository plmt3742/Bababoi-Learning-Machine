<script setup lang="ts">
defineProps<{
  title: string
  description: string
  eyebrow?: string
}>()
</script>

<template>
  <header class="page-header">
    <p v-if="eyebrow" class="page-header__eyebrow">{{ eyebrow }}</p>
    <h1 class="page-header__title">{{ title }}</h1>
    <p class="page-header__description">{{ description }}</p>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.page-header__eyebrow {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.page-header__title {
  font-size: var(--text-2xl);
  line-height: var(--text-2xl-leading);
  letter-spacing: -0.01em;
}

.page-header__description {
  max-width: 62ch;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

@media (max-width: 767px) {
  .page-header__title {
    font-size: var(--text-xl);
    line-height: var(--text-xl-leading);
  }
}
</style>
