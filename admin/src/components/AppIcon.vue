<script setup lang="ts">
import { computed } from 'vue'

type IconName =
  | 'dashboard'
  | 'alert'
  | 'users'
  | 'key'
  | 'file'
  | 'tasks'
  | 'spark'
  | 'audit'
  | 'system'
  | 'search'
  | 'refresh'
  | 'chevron'
  | 'arrow'
  | 'bell'
  | 'menu'
  | 'logout'
  | 'check'
  | 'close'
  | 'copy'
  | 'clock'
  | 'plus'
  | 'download'
  | 'filter'
  | 'shield'
  | 'server'
  | 'warning'

const props = withDefaults(defineProps<{ name: IconName; size?: number }>(), { size: 18 })

const ICONS: Record<IconName, string[]> = {
  dashboard: ['M4 4h6v7H4z', 'M14 4h6v4h-6z', 'M14 12h6v8h-6z', 'M4 15h6v5H4z'],
  alert: ['M12 4 3.5 19h17z', 'M12 9v4', 'M12 16.5v.01'],
  users: ['M16 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 18.5V20', 'M10 11a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4', 'M17 11a2.7 2.7 0 1 0 0-5.4', 'M20 20v-1.4a3.2 3.2 0 0 0-2.4-3.1'],
  key: ['M14.5 9.5a4 4 0 1 1-8 0 4 4 0 0 1 8 0', 'M14.5 9.5 20 4', 'M17.5 6.5 20 9', 'M15 9l2 2'],
  file: ['M5 3h9l5 5v13H5z', 'M14 3v5h5', 'M8 13h8', 'M8 17h6'],
  tasks: ['M9 6h11', 'M9 12h11', 'M9 18h11', 'M4 6l1.2 1.2L7.5 4.8', 'M4 12l1.2 1.2 2.3-2.4', 'M4 18l1.2 1.2 2.3-2.4'],
  spark: ['M13 2 4.5 13H11l-1 9 8.5-11H12z'],
  audit: ['M12 3 4.5 6v5.5c0 4.4 3 7.6 7.5 9.5 4.5-1.9 7.5-5.1 7.5-9.5V6z', 'm8.5 12 2.3 2.3 4.7-4.8'],
  system: ['M4 4h16v5H4z', 'M4 10.5h16v5H4z', 'M4 17h16v3H4z', 'M7 6.5h.01', 'M7 13h.01', 'M7 18.5h.01'],
  search: ['M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14', 'm16.2 16.2 4 4'],
  refresh: ['M20 11a8 8 0 0 0-14.8-4L3 10', 'M3 4v6h6', 'M4 13a8 8 0 0 0 14.8 4L21 14', 'M21 20v-6h-6'],
  chevron: ['m9 6 6 6-6 6'],
  arrow: ['M4 12h16', 'm14 6 6 6-6 6'],
  bell: ['M18 9a6 6 0 1 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9', 'M10 21h4'],
  menu: ['M4 7h16', 'M4 12h16', 'M4 17h16'],
  logout: ['M10 4H5v16h5', 'M14 8l4 4-4 4', 'M18 12H9'],
  check: ['m4 12 5 5L20 6'],
  close: ['M6 6l12 12', 'M18 6 6 18'],
  copy: ['M8 8h11v12H8z', 'M5 16V4h11'],
  clock: ['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18', 'M12 7v5l3 2'],
  plus: ['M12 5v14', 'M5 12h14'],
  download: ['M12 3v12', 'm7 10 5 5 5-5', 'M4 20h16'],
  filter: ['M4 6h16', 'M7 12h10', 'M10 18h4'],
  shield: ['M12 3 4.5 6v5.5c0 4.4 3 7.6 7.5 9.5 4.5-1.9 7.5-5.1 7.5-9.5V6z', 'M9.5 12.2 11.3 14l3.4-3.5'],
  server: ['M4 5h16v5H4z', 'M4 14h16v5H4z', 'M7 7.5h.01', 'M7 16.5h.01'],
  warning: ['M12 4 3.5 19h17z', 'M12 9v4', 'M12 16.5v.01'],
}

const paths = computed(() => ICONS[props.name])
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.65"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path v-for="(path, index) in paths" :key="index" :d="path" />
  </svg>
</template>
