<script setup lang="ts">
import { computed } from 'vue'

import type { TrendPoint } from '../types'

const props = withDefaults(
  defineProps<{
    points: TrendPoint[]
    tone?: 'blue' | 'amber'
    suffix?: string
    digits?: number
  }>(),
  { tone: 'blue', suffix: '', digits: 0 },
)

const WIDTH = 680
const HEIGHT = 214
const PAD = { left: 42, right: 14, top: 14, bottom: 34 }

const color = computed(() => (props.tone === 'amber' ? '#d88b18' : '#165dff'))
const gradientId = computed(() => `adm-chart-area-${props.tone}`)

const chart = computed(() => {
  const values = props.points.map((point) => point.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const spread = max - min || 1
  const low = min - spread * 0.22
  const high = max + spread * 0.22
  const plotWidth = WIDTH - PAD.left - PAD.right
  const plotHeight = HEIGHT - PAD.top - PAD.bottom

  const format = (value: number): string =>
    `${value.toFixed(props.digits)}${props.suffix}`

  const coords = props.points.map((point, index) => {
    const x =
      props.points.length > 1
        ? PAD.left + (index / (props.points.length - 1)) * plotWidth
        : PAD.left + plotWidth / 2
    const y = PAD.top + plotHeight - ((point.value - low) / (high - low)) * plotHeight
    return { ...point, x, y }
  })

  const line = coords
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(' ')
  const last = coords[coords.length - 1]
  const first = coords[0]
  const area = `${line} L ${last?.x ?? PAD.left} ${PAD.top + plotHeight} L ${
    first?.x ?? PAD.left
  } ${PAD.top + plotHeight} Z`

  const grid = [0, 0.25, 0.5, 0.75, 1].map((ratio) => ({
    y: PAD.top + plotHeight * ratio,
    label: format(high - (high - low) * ratio),
  }))

  return { coords, line, area, grid, format }
})
</script>

<template>
  <svg class="adm-chart-svg" :viewBox="`0 0 ${WIDTH} ${HEIGHT}`" role="img" aria-label="趋势图">
    <defs>
      <linearGradient :id="gradientId" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" :stop-color="color" stop-opacity="0.16" />
        <stop offset="100%" :stop-color="color" stop-opacity="0.01" />
      </linearGradient>
    </defs>

    <g>
      <line
        v-for="gridLine in chart.grid"
        :key="gridLine.y"
        :x1="PAD.left"
        :x2="WIDTH - PAD.right"
        :y1="gridLine.y"
        :y2="gridLine.y"
        stroke="#edf0f4"
        stroke-width="1"
      />
      <text
        v-for="gridLine in chart.grid"
        :key="`label-${gridLine.y}`"
        :x="PAD.left - 8"
        :y="gridLine.y + 3"
        fill="#8b95a4"
        font-size="10.5"
        font-family="Consolas, monospace"
        text-anchor="end"
      >
        {{ gridLine.label }}
      </text>
    </g>

    <path :d="chart.area" :fill="`url(#${gradientId})`" />
    <path
      :d="chart.line"
      fill="none"
      :stroke="color"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <g v-for="point in chart.coords" :key="point.label">
      <circle :cx="point.x" :cy="point.y" r="3" fill="#fff" :stroke="color" stroke-width="2" />
      <text
        :x="point.x"
        :y="HEIGHT - 10"
        fill="#8b95a4"
        font-size="10.5"
        font-family="Consolas, monospace"
        text-anchor="middle"
      >
        {{ point.label }}
      </text>
    </g>
  </svg>
</template>
