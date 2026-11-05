<script setup lang="ts">
defineProps<{
  title: string
  description: string
  eyebrow?: string
}>()
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p v-if="eyebrow" class="kicker">{{ eyebrow }}</p>
      <h1>{{ title }}</h1>
      <p>{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="page-head__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-6);
  flex-wrap: wrap;
  margin-bottom: var(--space-5);
}

.page-head__main {
  min-width: 0;
}

.page-head h1 {
  margin-top: 6px;
  font-size: var(--text-2xl);
  line-height: var(--text-2xl-leading);
  font-weight: 650;
  letter-spacing: -0.012em;
}

.page-head__main > p:last-child:not(.kicker) {
  max-width: 680px;
  margin-top: var(--space-1);
  color: var(--color-text-2);
  font-size: 15px;
  line-height: 24px;
  text-wrap: pretty;
}

.page-head__actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}

@media (max-width: 767px) {
  .page-head {
    gap: var(--space-3);
    margin-bottom: var(--space-4);
  }

  .page-head h1 {
    font-size: 24px;
    line-height: 32px;
  }

  .page-head__main > p:last-child:not(.kicker) {
    font-size: var(--text-sm);
    line-height: 22px;
  }

  .page-head__actions {
    width: 100%;
  }

  .page-head__actions :deep(.btn) {
    width: 100%;
  }
}
</style>
