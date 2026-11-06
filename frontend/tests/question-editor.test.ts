import { describe, expect, it } from 'vitest'
import {
  MAX_CHOICE_OPTIONS,
  countBlankMarkers,
  optionLabel,
  syncBlankAnswers,
  validateBlankAnswers,
  validateChoiceOptions,
} from '../src/utils/questionEditor'

describe('question editor helpers', () => {
  it('matches the backend choice option ceiling', () => {
    expect(MAX_CHOICE_OPTIONS).toBe(24)
    expect(optionLabel(0)).toBe('A')
    expect(optionLabel(23)).toBe('X')
  })

  it('counts and syncs blank markers', () => {
    const content = '第一空 ___，第二空 ___。'
    expect(countBlankMarkers(content)).toBe(2)
    expect(syncBlankAnswers(content, [{ answer_md: '1' }])).toEqual([
      { answer_md: '1' },
      { answer_md: '' },
    ])
  })

  it('rejects empty or mismatched blanks', () => {
    expect(validateBlankAnswers('没有空位', [])).toContain('空位标记')
    expect(validateBlankAnswers('___ ___', [{ answer_md: '1' }])).toContain('答案却是 1 个')
    expect(validateBlankAnswers('___', [{ answer_md: '' }])).toContain('还没有填写答案')
  })

  it('rejects empty choice options', () => {
    expect(validateChoiceOptions([{ content_md: 'A' }])).toContain('至少需要 2 个选项')
    expect(validateChoiceOptions([{ content_md: 'A' }, { content_md: '' }])).toContain(
      '还没有填写内容',
    )
  })
})
