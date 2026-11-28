import { describe, expect, it } from 'vitest'
import {
  extractChoiceAnswerLabel,
  resolveDueReason,
  resolvePracticeShortcut,
} from '../src/utils/practice'

describe('extractChoiceAnswerLabel', () => {
  it('recognizes common single-choice answer formats', () => {
    expect(extractChoiceAnswerLabel('选 A')).toBe('A')
    expect(extractChoiceAnswerLabel('答案：B')).toBe('B')
    expect(extractChoiceAnswerLabel('**C**')).toBe('C')
    expect(extractChoiceAnswerLabel('d.')).toBe('D')
    expect(extractChoiceAnswerLabel('故选 E')).toBe('E')
    expect(extractChoiceAnswerLabel('选项 F')).toBe('F')
  })

  it('rejects ambiguous or non-label text', () => {
    expect(extractChoiceAnswerLabel('AB 两点')).toBe('')
    expect(extractChoiceAnswerLabel('不会')).toBe('')
    expect(extractChoiceAnswerLabel('')).toBe('')
    expect(extractChoiceAnswerLabel(null)).toBe('')
  })
})

describe('resolvePracticeShortcut', () => {
  const base = {
    key: 'a',
    code: 'KeyA',
    revealed: false,
    submitting: false,
    choiceLabels: ['A', 'B', 'C', 'D'],
    editable: false,
    activatable: false,
  }

  it('selects an available choice letter before reveal', () => {
    expect(resolvePracticeShortcut(base)).toEqual({ type: 'choice', label: 'A' })
    expect(resolvePracticeShortcut({ ...base, key: 'z', code: 'KeyZ' })).toBeNull()
    expect(resolvePracticeShortcut({ ...base, revealed: true })).toBeNull()
  })

  it('advances with Space except on editable or activatable targets', () => {
    expect(resolvePracticeShortcut({ ...base, key: ' ', code: 'Space' })).toEqual({
      type: 'reveal',
    })
    expect(resolvePracticeShortcut({ ...base, key: ' ', code: 'Space', editable: true })).toBeNull()
    expect(
      resolvePracticeShortcut({ ...base, key: ' ', code: 'Space', activatable: true }),
    ).toBeNull()
    expect(
      resolvePracticeShortcut({ ...base, key: ' ', code: 'Space', ctrlKey: true }),
    ).toBeNull()
  })

  it('grades with 1/2 only after reveal and when not submitting', () => {
    expect(resolvePracticeShortcut({ ...base, key: '1', code: 'Digit1' })).toBeNull()
    expect(resolvePracticeShortcut({ ...base, key: '1', code: 'Digit1', revealed: true })).toEqual({
      type: 'grade',
      correct: false,
    })
    expect(
      resolvePracticeShortcut({ ...base, key: '2', code: 'Digit2', revealed: true }),
    ).toEqual({ type: 'grade', correct: true })
    expect(
      resolvePracticeShortcut({
        ...base,
        key: '2',
        code: 'Digit2',
        revealed: true,
        submitting: true,
      }),
    ).toBeNull()
  })
})

describe('resolveDueReason', () => {
  const now = new Date('2026-11-28T00:00:00Z')

  it('treats never-practiced questions as due', () => {
    expect(resolveDueReason('mastered', null, now)).toBe('never')
    expect(resolveDueReason('unmastered', undefined, now)).toBe('never')
  })

  it('uses 1 / 3 / 7 day intervals', () => {
    expect(resolveDueReason('unmastered', '2026-11-27T00:00:00Z', now)).toBe('unmastered_1d')
    expect(resolveDueReason('reviewing', '2026-11-25T00:00:00Z', now)).toBe('reviewing_3d')
    expect(resolveDueReason('mastered', '2026-11-21T00:00:00Z', now)).toBe('mastered_7d')
    expect(resolveDueReason('mastered', '2026-11-27T00:00:00Z', now)).toBeNull()
  })

  it('does not schedule future or invalid timestamps as due', () => {
    expect(resolveDueReason('unmastered', '2026-12-01T00:00:00Z', now)).toBeNull()
    expect(resolveDueReason('unmastered', 'not-a-time', now)).toBe('never')
  })
})
