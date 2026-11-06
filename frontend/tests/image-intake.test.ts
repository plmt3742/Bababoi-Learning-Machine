import { describe, expect, it } from 'vitest'
import type { ImageExtractionResult } from '../src/api/types'
import {
  canSelectImageItem,
  createImageItemDrafts,
  firstDetectedSubject,
  isImageItemEdited,
  toImageQuestionPayload,
} from '../src/utils/imageIntake'

const extraction: ImageExtractionResult = {
  image_path: 'uploads/1/mock.jpg',
  warnings: ['第 3 题仅部分可见'],
  questions: [
    {
      index: 1,
      content_md: '求极值。',
      question_type: 'solve',
      subject: '高等数学',
      chapter: '导数与极值',
      difficulty: 'medium',
      options: null,
      blanks: null,
      has_figure: false,
      warnings: [],
      incomplete: false,
    },
    {
      index: 2,
      content_md: '填空 ___。',
      question_type: 'blank',
      subject: null,
      chapter: null,
      difficulty: null,
      options: null,
      blanks: null,
      has_figure: false,
      warnings: ['空位答案缺失'],
      incomplete: true,
    },
  ],
}

describe('image intake helpers', () => {
  it('normalizes nullable extraction fields', () => {
    const drafts = createImageItemDrafts(extraction)
    expect(drafts).toHaveLength(2)
    expect(drafts[1].options).toEqual([])
    expect(drafts[1].blanks).toEqual([])
    expect(drafts[1].selected).toBe(false)
    expect(firstDetectedSubject(extraction)).toBe('高等数学')
  })

  it('blocks incomplete items until the stem is edited', () => {
    const item = createImageItemDrafts(extraction)[1]
    expect(canSelectImageItem(item)).toBe(false)

    const edited = { ...item, content_md: '填空 ___（已补全）。' }
    expect(isImageItemEdited(edited)).toBe(true)
    expect(canSelectImageItem(edited)).toBe(true)
  })

  it('builds a solve payload without options or blanks', () => {
    const item = createImageItemDrafts(extraction)[0]
    const payload = toImageQuestionPayload(item, '高等数学', 'uploads/1/mock.jpg')
    expect(payload.question_type).toBe('solve')
    expect(payload.options).toBeUndefined()
    expect(payload.blanks).toBeUndefined()
    expect(payload.image_path).toBe('uploads/1/mock.jpg')
  })
})
