import type { StatsTrendPoint } from '../api/types'

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

export function formatTrendDay(date: string): string {
  const match = /^\d{4}-(\d{2})-(\d{2})/.exec(date)
  return match ? `${match[1]}-${match[2]}` : date
}

export function formatTrendDayShort(date: string): string {
  const match = /^\d{4}-\d{2}-(\d{2})/.exec(date)
  return match ? match[1] : date
}

export function formatStatsTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'

  const pad = (part: number): string => String(part).padStart(2, '0')
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(
    date.getMinutes(),
  )}`
}
