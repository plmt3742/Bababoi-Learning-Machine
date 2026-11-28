import { describe, expect, it } from 'vitest'
import {
  clampAccuracy,
  fillRecentSevenDays,
  formatAccuracy,
  summarizeTrend,
} from '../src/utils/stats'

describe('stats helpers', () => {
  it('formats accuracy and treats null as unknown', () => {
    expect(formatAccuracy(0.5, 10)).toBe('50%')
    expect(formatAccuracy(0, 0)).toBe('—')
    expect(formatAccuracy(null, 10)).toBe('—')
    expect(formatAccuracy(undefined, 10)).toBe('—')
  })

  it('clamps out-of-range ratios', () => {
    expect(clampAccuracy(-1)).toBe(0)
    expect(clampAccuracy(2)).toBe(1)
    expect(clampAccuracy(Number.NaN)).toBe(0)
  })

  it('summarizes trend points', () => {
    expect(
      summarizeTrend([
        { date: '2026-11-06', practice_count: 2, correct_count: 1 },
        { date: '2026-11-07', practice_count: 3, correct_count: 2 },
      ]),
    ).toEqual({ practiceCount: 5, correctCount: 3, accuracy: 0.6 })
  })
})

describe('fillRecentSevenDays', () => {
  it('returns a continuous, ascending 7-day window ending today', () => {
    const filled = fillRecentSevenDays([], new Date('2026-11-27T04:00:00Z'))

    expect(filled.map((point) => point.date)).toEqual([
      '2026-11-21',
      '2026-11-22',
      '2026-11-23',
      '2026-11-24',
      '2026-11-25',
      '2026-11-26',
      '2026-11-27',
    ])
    expect(
      filled.every((point) => point.practice_count === 0 && point.correct_count === 0),
    ).toBe(true)
  })

  it('keeps existing buckets and zero-fills the missing days', () => {
    const filled = fillRecentSevenDays(
      [{ date: '2026-11-25', practice_count: 3, correct_count: 2 }],
      new Date('2026-11-27T04:00:00Z'),
    )

    expect(filled[4]).toEqual({ date: '2026-11-25', practice_count: 3, correct_count: 2 })
    expect(filled.filter((point) => point.practice_count === 0)).toHaveLength(6)
  })

  it('anchors on the Shanghai calendar day, ignores outside points, and keeps input intact', () => {
    const input = [{ date: '2026-11-19', practice_count: 9, correct_count: 9 }]
    const filled = fillRecentSevenDays(input, new Date('2026-11-27T20:00:00Z'))

    expect(filled.at(-1)?.date).toBe('2026-11-28')
    expect(filled.some((point) => point.date === '2026-11-19')).toBe(false)
    expect(input).toEqual([{ date: '2026-11-19', practice_count: 9, correct_count: 9 }])
  })
})
