import { describe, expect, it } from 'vitest'
import { parseApiTime, parseApiTimeOrNull } from '../src/utils/time'

describe('parseApiTime', () => {
  it('treats naive backend timestamps as UTC', () => {
    expect(parseApiTime('2026-11-11T10:43:58').toISOString()).toBe('2026-11-11T10:43:58.000Z')
    expect(parseApiTime('2026-11-11T10:43:58.123456').toISOString()).toBe(
      '2026-11-11T10:43:58.123Z',
    )
    expect(parseApiTime('2026-11-11T10:43').toISOString()).toBe('2026-11-11T10:43:00.000Z')
    expect(parseApiTime('2026-11-11 10:43:58').toISOString()).toBe('2026-11-11T10:43:58.000Z')
  })

  it('keeps explicit time zones untouched', () => {
    expect(parseApiTime('2026-11-11T10:43:58Z').toISOString()).toBe('2026-11-11T10:43:58.000Z')
    expect(parseApiTime('2026-11-11T18:43:58+08:00').toISOString()).toBe(
      '2026-11-11T10:43:58.000Z',
    )
  })

  it('leaves date-only values as UTC midnight', () => {
    expect(parseApiTime('2026-11-11').toISOString()).toBe('2026-11-11T00:00:00.000Z')
  })

  it('returns an invalid date for unparseable input', () => {
    expect(Number.isNaN(parseApiTime('not-a-date').getTime())).toBe(true)
  })
})

describe('parseApiTimeOrNull', () => {
  it('returns null for missing or invalid values', () => {
    expect(parseApiTimeOrNull(null)).toBeNull()
    expect(parseApiTimeOrNull(undefined)).toBeNull()
    expect(parseApiTimeOrNull('')).toBeNull()
    expect(parseApiTimeOrNull('not-a-date')).toBeNull()
  })

  it('parses naive values as UTC', () => {
    expect(parseApiTimeOrNull('2026-11-11T10:43:58')?.toISOString()).toBe(
      '2026-11-11T10:43:58.000Z',
    )
  })
})
