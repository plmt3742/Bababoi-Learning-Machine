<script setup lang="ts">
withDefaults(defineProps<{ size?: number }>(), { size: 20 })
</script>

<template>
  <svg
    class="brand-mark"
    :width="size"
    :height="size"
    viewBox="0 0 20 20"
    aria-hidden="true"
    focusable="false"
  >
    <rect class="brand-mark__accent" x="1" y="1" width="4" height="4" rx="0.6" />
    <rect class="brand-mark__muted" x="8" y="1" width="4" height="4" rx="0.6" />
    <rect class="brand-mark__muted" x="15" y="1" width="4" height="4" rx="0.6" />
    <rect class="brand-mark__muted" x="1" y="8" width="4" height="4" rx="0.6" />
    <rect class="brand-mark__accent" x="8" y="8" width="4" height="4" rx="0.6" />
    <rect class="brand-mark__muted" x="15" y="8" width="4" height="4" rx="0.6" />
    <rect class="brand-mark__muted" x="1" y="15" width="4" height="4" rx="0.6" />
    <rect class="brand-mark__muted" x="8" y="15" width="4" height="4" rx="0.6" />
    <rect class="brand-mark__accent" x="15" y="15" width="4" height="4" rx="0.6" />
  </svg>
</template>

<style scoped>
.brand-mark {
  flex: none;
  display: block;
}

.brand-mark__accent {
  fill: var(--color-primary);
}

.brand-mark__muted {
  fill: var(--color-border-strong);
}
</style>
