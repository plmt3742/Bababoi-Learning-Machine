import { describe, expect, it } from 'vitest'
import { clampAccuracy, formatAccuracy, summarizeTrend } from '../src/utils/stats'

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
