import { describe, expect, it } from 'vitest'
import {
  MAX_CHOICE_OPTIONS,
  countBlankMarkers,
  insertLatexTemplate,
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

  it('inserts a LaTeX template at the selection and moves the caret inside', () => {
    expect(insertLatexTemplate('ab', 1, 1, '\\frac{}{}', 6)).toEqual({
      value: 'a\\frac{}{}b',
      caret: 7,
    })
    expect(insertLatexTemplate('abcd', 1, 3, '\\sqrt{}', 6)).toEqual({
      value: 'a\\sqrt{}d',
      caret: 7,
    })
    expect(insertLatexTemplate('ab', 99, 99, '$ $', 1)).toEqual({ value: 'ab$ $', caret: 3 })
  })
})
