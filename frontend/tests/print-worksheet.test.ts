import { describe, expect, it } from 'vitest'
import { buildPrintQuery, settleWithConcurrency } from '../src/utils/printWorksheet'

describe('buildPrintQuery', () => {
  it('keeps the active filters and trims whitespace', () => {
    expect(
      buildPrintQuery({
        q: '  极限  ',
        subject: ' 高等数学 ',
        tag: ' 洛必达 ',
        mastery_status: 'unmastered',
      }),
    ).toEqual({
      q: '极限',
      subject: '高等数学',
      tag: '洛必达',
      mastery_status: 'unmastered',
    })
  })

  it('drops empty values so the print route stays clean', () => {
    expect(buildPrintQuery({ q: '   ', subject: '', tag: null, mastery_status: undefined })).toEqual(
      {},
    )
  })
})

describe('settleWithConcurrency', () => {
  it('preserves input order and isolates a rejected worker', async () => {
    const results = await settleWithConcurrency([1, 2, 3, 4], 2, async (value) => {
      if (value === 3) throw new Error('boom')
      return value * 10
    })

    expect(results[0]).toEqual({ status: 'fulfilled', value: 10 })
    expect(results[1]).toEqual({ status: 'fulfilled', value: 20 })
    expect(results[2]?.status).toBe('rejected')
    expect(results[3]).toEqual({ status: 'fulfilled', value: 40 })
  })

  it('never runs more workers than the limit', async () => {
    let active = 0
    let peak = 0
    const gates: Array<() => void> = []

    const pending = settleWithConcurrency([0, 1, 2, 3, 4, 5], 3, async (value) => {
      active += 1
      peak = Math.max(peak, active)
      await new Promise<void>((resolve) => gates.push(resolve))
      active -= 1
      return value
    })

    expect(active).toBe(3)

    for (let step = 0; step < 24 && gates.length > 0; step += 1) {
      gates.shift()?.()
      await Promise.resolve()
      await Promise.resolve()
    }

    const results = await pending
    expect(peak).toBe(3)
    expect(results.map((result) => (result.status === 'fulfilled' ? result.value : -1))).toEqual([
      0, 1, 2, 3, 4, 5,
    ])
  })

  it('handles an empty list and a non-positive limit', async () => {
    await expect(settleWithConcurrency([], 3, async () => 1)).resolves.toEqual([])
    const results = await settleWithConcurrency([7], 0, async (value) => value)
    expect(results).toEqual([{ status: 'fulfilled', value: 7 }])
  })
})
