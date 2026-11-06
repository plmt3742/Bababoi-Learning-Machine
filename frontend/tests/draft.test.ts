import { describe, expect, it } from 'vitest'
import {
  chooseDraftCandidate,
  hasMeaningfulDraftContent,
  normalizeDraftContent,
} from '../src/utils/draft'

describe('draft helpers', () => {
  it('normalizes malformed draft content defensively', () => {
    const content = normalizeDraftContent({
      subject: 42,
      question_type: 'unknown',
      tags: [' 高数 ', '', 3],
      options: 'not-an-array',
      blanks: [{ answer_md: '1' }],
      choice_correct_label: 'a',
    })

    expect(content.subject).toBe('')
    expect(content.question_type).toBe('solve')
    expect(content.tags).toEqual(['高数'])
    expect(content.options).toEqual([])
    expect(content.blanks).toEqual([{ answer_md: '1' }])
    expect(content.choice_correct_label).toBe('A')
  })

  it('detects meaningful work and picks the freshest candidate', () => {
    const empty = normalizeDraftContent({})
    expect(hasMeaningfulDraftContent(empty)).toBe(false)

    const content = normalizeDraftContent({ content_md: '题干' })
    expect(hasMeaningfulDraftContent(content)).toBe(true)

    const candidate = chooseDraftCandidate(
      {
        content,
        client_updated_at: '2026-11-07T01:00:00Z',
        server_version: 1,
      },
      {
        content,
        version: 2,
        updated_at: '2026-11-07T02:00:00Z',
      },
    )

    expect(candidate?.source).toBe('server')
    expect(candidate?.version).toBe(2)
  })
})
