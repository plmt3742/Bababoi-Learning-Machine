import type { StatsTrendPoint } from '../api/types'
import { parseApiTime } from './time'

export function clampAccuracy(value: number): number {
  if (!Number.isFinite(value)) return 0
  return Math.min(1, Math.max(0, value))
}

export function formatAccuracy(accuracy: number | null | undefined, totalCount: number): string {
  if (totalCount <= 0 || accuracy === null || accuracy === undefined) return '—'
  return `${Math.round(clampAccuracy(accuracy) * 100)}%`
}

export function percentOf(value: number, total: number): number {
  if (total <= 0) return 0
  return Math.min(100, Math.max(0, (value / total) * 100))
}

export function summarizeTrend(points: StatsTrendPoint[]): {
  practiceCount: number
  correctCount: number
  accuracy: number
} {
  let practiceCount = 0
  let correctCount = 0

  for (const point of points) {
    practiceCount += Math.max(0, point.practice_count)
    correctCount += Math.max(0, point.correct_count)
  }

  return {
    practiceCount,
    correctCount,
    accuracy: practiceCount > 0 ? correctCount / practiceCount : 0,
  }
}

const SHANGHAI_DAY = new Intl.DateTimeFormat('en-US', {
  timeZone: 'Asia/Shanghai',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})

function shanghaiDayKey(date: Date): string {
  const parts = SHANGHAI_DAY.formatToParts(date)
  const part = (type: string): string =>
    parts.find((item) => item.type === type)?.value ?? ''
  return `${part('year')}-${part('month')}-${part('day')}`
}

/**
 * 后端 `recent_trend` 只返回有练习记录的日期（21 号 §2.1），图表要的「近 7 天」
 * 必须在展示层补成连续 7 天。锚点用 Asia/Shanghai，与后端 CHINA_TZ 的分桶一致；
 * 用浏览器本地时区会在 UTC 跨日边界出现「今天」与后端不同。
 */
export function fillRecentSevenDays(
  points: StatsTrendPoint[],
  now: Date = new Date(),
): StatsTrendPoint[] {
  const byDate = new Map<string, StatsTrendPoint>()
  for (const point of points) {
    const key = point.date.slice(0, 10)
    if (!byDate.has(key)) byDate.set(key, point)
  }

  const anchor = new Date(`${shanghaiDayKey(now)}T00:00:00Z`)
  const filled: StatsTrendPoint[] = []
  for (let offset = 6; offset >= 0; offset -= 1) {
    const key = new Date(anchor.getTime() - offset * 86_400_000)
      .toISOString()
      .slice(0, 10)
    const point = byDate.get(key)
    filled.push({
      date: key,
      practice_count: point?.practice_count ?? 0,
      correct_count: point?.correct_count ?? 0,
    })
  }
  return filled
}

export function formatTrendDay(date: string): string {
  const match = /^\d{4}-(\d{2})-(\d{2})/.exec(date)
  return match ? `${match[1]}-${match[2]}` : date
}

export function formatTrendDayShort(date: string): string {
  const match = /^\d{4}-\d{2}-(\d{2})/.exec(date)
  return match ? match[1] : date
}

export function formatStatsTime(value: string): string {
  const date = parseApiTime(value)
  if (Number.isNaN(date.getTime())) return '—'

  const pad = (part: number): string => String(part).padStart(2, '0')
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(
    date.getMinutes(),
  )}`
}
