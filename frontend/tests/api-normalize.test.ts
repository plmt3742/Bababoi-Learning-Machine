import { describe, expect, it } from 'vitest'
import { normalizeGenerateResponse } from '../src/api/questions'

describe('normalizeGenerateResponse', () => {
  it('keeps the three-segment task payload', () => {
    const result = normalizeGenerateResponse({
      tasks: [
        { task_id: 11, target_index: 1, difficulty: 'easy' },
        { task_id: 12, target_index: 2, difficulty: 'medium' },
      ],
    })

    expect(result.tasks).toEqual([
      { task_id: 11, target_index: 1, difficulty: 'easy' },
      { task_id: 12, target_index: 2, difficulty: 'medium' },
    ])
  })

  it('falls back to the legacy task_id shape', () => {
    expect(normalizeGenerateResponse({ task_id: 7 })).toEqual({
      tasks: [{ task_id: 7, target_index: null, difficulty: null }],
    })
  })

  it('rejects malformed payloads', () => {
    expect(() => normalizeGenerateResponse({})).toThrow('生成接口返回格式不正确')
    expect(() => normalizeGenerateResponse({ tasks: [{ target_index: 1 }] })).toThrow(
      '生成接口返回格式不正确',
    )
  })
})
