<script setup lang="ts">
import { computed } from 'vue'

type MascotState = 'default' | 'curious' | 'thinking' | 'happy' | 'error'

const SOURCES: Record<MascotState, string> = {
  default: new URL('../../assets/mascot/mascot-body.svg', import.meta.url).href,
  curious: new URL('../../assets/mascot/states/state-curious.svg', import.meta.url).href,
  thinking: new URL('../../assets/mascot/states/state-thinking.svg', import.meta.url).href,
  happy: new URL('../../assets/mascot/states/state-happy.svg', import.meta.url).href,
  error: new URL('../../assets/mascot/states/state-error.svg', import.meta.url).href,
}

const props = withDefaults(
  defineProps<{
    state?: MascotState
    size?: number
    label?: string
  }>(),
  {
    state: 'default',
    size: 40,
    label: '',
  },
)

const src = computed(() => SOURCES[props.state])
const boxStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
  fontSize: `${props.size}px`,
}))
const accessible = computed(() => props.label.length > 0)
</script>

<template>
  <span
    class="mascot-3d"
    :style="boxStyle"
    :role="accessible ? 'img' : undefined"
    :aria-label="accessible ? label : undefined"
    :aria-hidden="accessible ? undefined : 'true'"
  >
    <img class="mascot-3d__face" :src="src" alt="" draggable="false" />
  </span>
</template>

<style scoped>
.mascot-3d {
  display: inline-grid;
  flex: none;
  place-items: center;
  line-height: 0;
}

.mascot-3d__face {
  width: 100%;
  height: 100%;
  object-fit: contain;
  filter: drop-shadow(0.045em 0.045em 0 var(--color-primary));
}
</style>
