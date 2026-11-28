<script setup lang="ts">
defineProps<{
  eyebrow?: string
  title: string
  description?: string
}>()
</script>

<template>
  <header class="adm-page-head">
    <div class="adm-page-head__copy">
      <p v-if="eyebrow" class="adm-eyebrow">{{ eyebrow }}</p>
      <h1>{{ title }}</h1>
      <p v-if="description" class="adm-page-head__desc">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="adm-page-head__actions">
      <slot name="actions" />
    </div>
  </header>
</template>
