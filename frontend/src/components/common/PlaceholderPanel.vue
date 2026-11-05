<script setup lang="ts">
defineProps<{
  hint: string
  task: string
}>()
</script>

<template>
  <section class="paper placeholder-panel">
    <div class="placeholder-panel__illustration" aria-hidden="true">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M5 4.5A1.5 1.5 0 0 1 6.5 3H19v18H6.5A1.5 1.5 0 0 1 5 19.5z" />
        <path d="M5 17.5A1.5 1.5 0 0 1 6.5 16H19" />
        <path d="M9 7h6M9 11h4" />
      </svg>
    </div>

    <div class="placeholder-panel__copy">
      <h3 class="placeholder-panel__title">页面骨架已就位</h3>
      <p class="placeholder-panel__hint">{{ hint }}</p>
      <p class="placeholder-panel__task">{{ task }}</p>
    </div>

    <div v-if="$slots.action" class="placeholder-panel__action">
      <slot name="action" />
    </div>
  </section>
</template>

<style scoped>
.placeholder-panel {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-2);
  min-height: var(--layout-empty-min-height);
  padding: var(--space-5) var(--space-6) var(--space-6);
}

.placeholder-panel__illustration {
  display: grid;
  width: var(--layout-empty-glyph);
  height: var(--layout-empty-glyph);
  margin: 2px 0 var(--space-1);
  place-items: center;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text-3);
}

.placeholder-panel__illustration svg {
  width: 22px;
  height: 22px;
}

.placeholder-panel__copy {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.placeholder-panel__title {
  font-size: var(--text-base);
  line-height: 24px;
  font-weight: 650;
}

.placeholder-panel__hint {
  max-width: 52ch;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.placeholder-panel__task {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
  letter-spacing: 0.02em;
  overflow-wrap: anywhere;
}

.placeholder-panel__action {
  margin-top: var(--space-1);
}

@media (max-width: 767px) {
  .placeholder-panel {
    padding: var(--space-5);
  }
}
</style>
