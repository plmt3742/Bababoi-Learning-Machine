<script setup lang="ts">
import type { Tone } from '../types'

withDefaults(defineProps<{ tone?: Tone; label: string; dot?: boolean }>(), {
  tone: 'neutral',
  dot: true,
})
</script>

<template>
  <span class="adm-tag" :class="`adm-tag--${tone}`">
    <span v-if="dot" class="adm-tag__dot" aria-hidden="true" />
    {{ label }}
  </span>
</template>
