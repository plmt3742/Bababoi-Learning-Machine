<script setup lang="ts">
import AppIcon from './AppIcon.vue'

type IconName =
  | 'users'
  | 'file'
  | 'spark'
  | 'tasks'
  | 'system'
  | 'alert'
  | 'clock'
  | 'audit'
  | 'key'
  | 'check'
  | 'close'
  | 'shield'
  | 'download'

withDefaults(
  defineProps<{
    label: string
    value: string
    unit?: string
    hint?: string
    trend?: string
    trendTone?: 'positive' | 'negative' | 'neutral'
    danger?: boolean
    icon?: IconName
  }>(),
  {
    unit: '',
    hint: '',
    trend: '',
    trendTone: 'neutral',
    danger: false,
    icon: undefined,
  },
)
</script>

<template>
  <article class="adm-kpi">
    <div class="adm-kpi__top">
      <AppIcon v-if="icon" :name="icon" :size="14" />
      <span>{{ label }}</span>
    </div>
    <p class="adm-kpi__value" :class="{ 'adm-kpi__value--danger': danger }">
      {{ value }}<small v-if="unit">{{ unit }}</small>
    </p>
    <div class="adm-kpi__foot">
      <span v-if="trend" class="adm-trend" :class="`adm-trend--${trendTone}`">{{ trend }}</span>
      <span v-if="hint">{{ hint }}</span>
    </div>
  </article>
</template>
