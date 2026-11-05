/**
 * FE-020 question structure helpers.
 *
 * Keeps the create-page drafts (plain text containers) separate from the API
 * payload types while mirroring the backend's `question.py` validation rules:
 * choice labels are sequential A..F, and blank answers map 1:1 to `___` runs.
 */
import type { QuestionBlank, QuestionOption } from '../api/types'

export const MIN_CHOICE_OPTIONS = 2
export const MAX_CHOICE_OPTIONS = 6
export const MAX_BLANK_MARKERS = 20
export const MAX_OPTION_CONTENT_LENGTH = 5000
export const MAX_ANSWER_CONTENT_LENGTH = 5000

export interface ChoiceOptionDraft {
  content_md: string
}

export interface BlankAnswerDraft {
  answer_md: string
}

const MARKER_RUN = /_{3,}/g

const CIRCLED_NUMBERS = [
  '①',
  '②',
  '③',
  '④',
  '⑤',
  '⑥',
  '⑦',
  '⑧',
  '⑨',
  '⑩',
  '⑪',
  '⑫',
  '⑬',
  '⑭',
  '⑮',
  '⑯',
  '⑰',
  '⑱',
  '⑲',
  '⑳',
]

export function createChoiceOption(content_md = ''): ChoiceOptionDraft {
  return { content_md }
}

export function createBlankAnswer(answer_md = ''): BlankAnswerDraft {
  return { answer_md }
}

export function createDefaultChoiceOptions(): ChoiceOptionDraft[] {
  return [createChoiceOption(), createChoiceOption()]
}

/** A, B, C... capped by MAX_CHOICE_OPTIONS in the editor. */
export function optionLabel(index: number): string {
  return String.fromCharCode(65 + index)
}

/** Count `___` runs exactly like the backend's `re.compile(r"_{3,}")`. */
export function countBlankMarkers(content: string): number {
  return content.match(MARKER_RUN)?.length ?? 0
}

/** Resize answers so their count matches the markers, preserving shared slots. */
export function syncBlankAnswers(content: string, blanks: BlankAnswerDraft[]): BlankAnswerDraft[] {
  const markerCount = countBlankMarkers(content)
  const next = blanks.slice(0, markerCount).map((blank) => ({
    answer_md: blank.answer_md,
  }))

  while (next.length < markerCount) next.push(createBlankAnswer())

  return next
}

export function insertBlankMarker(content: string): string {
  if (!content.trim()) return '___'
  return /[\s]$/.test(content) ? `${content}___` : `${content} ___`
}

function findBlankRanges(content: string): Array<{ start: number; end: number }> {
  const ranges: Array<{ start: number; end: number }> = []
  const pattern = new RegExp(MARKER_RUN.source, 'g')
  let match: RegExpExecArray | null = pattern.exec(content)

  while (match) {
    ranges.push({ start: match.index, end: match.index + match[0].length })
    match = pattern.exec(content)
  }

  return ranges
}

/** Remove the nth (0-based) marker so the answer row can be deleted with it. */
export function removeBlankMarkerAt(content: string, index: number): string {
  const range = findBlankRanges(content)[index]
  if (!range) return content

  let start = range.start
  if (start > 0 && content[start - 1] === ' ') start -= 1

  return content.slice(0, start) + content.slice(range.end)
}

export function toChoiceOptions(drafts: ChoiceOptionDraft[]): QuestionOption[] {
  return drafts.map((draft, index) => ({
    label: optionLabel(index),
    content_md: draft.content_md.trim(),
  }))
}

export function toBlankAnswers(drafts: BlankAnswerDraft[]): QuestionBlank[] {
  return drafts.map((draft, index) => ({
    index: index + 1,
    answer_md: draft.answer_md.trim(),
  }))
}

export function validateChoiceOptions(drafts: ChoiceOptionDraft[]): string | null {
  if (drafts.length < MIN_CHOICE_OPTIONS) {
    return `选择题至少需要 ${MIN_CHOICE_OPTIONS} 个选项`
  }
  if (drafts.length > MAX_CHOICE_OPTIONS) {
    return `选择题最多支持 ${MAX_CHOICE_OPTIONS} 个选项`
  }

  for (let index = 0; index < drafts.length; index += 1) {
    if (!drafts[index].content_md.trim()) {
      return `选项 ${optionLabel(index)} 还没有填写内容`
    }
  }

  return null
}

export function validateBlankAnswers(content: string, drafts: BlankAnswerDraft[]): string | null {
  const markerCount = countBlankMarkers(content)

  if (markerCount === 0) {
    return '题干中还没有空位标记，请用连续三个下划线 ___ 表示一个空位'
  }
  if (markerCount > MAX_BLANK_MARKERS) {
    return `题干最多支持 ${MAX_BLANK_MARKERS} 个空位`
  }
  if (drafts.length !== markerCount) {
    return `题干有 ${markerCount} 个空位，答案却是 ${drafts.length} 个`
  }

  for (let index = 0; index < drafts.length; index += 1) {
    if (!drafts[index].answer_md.trim()) {
      return `第 ${index + 1} 空还没有填写答案`
    }
  }

  return null
}

function circledNumber(value: number): string {
  return CIRCLED_NUMBERS[value - 1] ?? `(${value})`
}

function findMathEnd(source: string, start: number, delimiter: string): number {
  let index = start

  while (index < source.length) {
    if (source[index] === '\\') {
      index += 2
      continue
    }

    if (source.startsWith(delimiter, index)) {
      if (delimiter === '$' && source[index + 1] === '$') {
        index += 2
        continue
      }
      return index + delimiter.length
    }

    index += 1
  }

  return -1
}

/**
 * Make blank markers visible in a Markdown preview: `___` becomes `` `___①` ``.
 * Math spans are preserved so `$...$` still reaches KaTeX untouched.
 */
export function buildBlankPreview(content: string): string {
  let result = ''
  let index = 0
  let blankIndex = 0

  while (index < content.length) {
    if (content[index] === '\\') {
      result += content.slice(index, index + 2)
      index += 2
      continue
    }

    if (content[index] === '$') {
      const delimiter = content[index + 1] === '$' ? '$$' : '$'
      const end = findMathEnd(content, index + delimiter.length, delimiter)

      if (end !== -1) {
        result += content.slice(index, end)
        index = end
        continue
      }
    }

    const marker = /^_{3,}/.exec(content.slice(index))
    if (marker) {
      blankIndex += 1
      result += `\`___${circledNumber(blankIndex)}\``
      index += marker[0].length
      continue
    }

    result += content[index]
    index += 1
  }

  return result
}
