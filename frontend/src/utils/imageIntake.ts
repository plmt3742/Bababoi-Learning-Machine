import type {
  Difficulty,
  ExtractedImageQuestion,
  ImageExtractionResult,
  Question,
  QuestionCreate,
  QuestionType,
} from '../api/types'
import {
  countBlankMarkers,
  createBlankAnswer,
  createChoiceOption,
  createDefaultChoiceOptions,
  syncBlankAnswers,
  toBlankAnswers,
  toChoiceOptions,
  validateBlankAnswers,
  validateChoiceOptions,
} from './questionEditor'
import type { BlankAnswerDraft, ChoiceOptionDraft } from './questionEditor'

export const MAX_IMAGE_CONTENT_LENGTH = 5000

export interface ImageItemDraft {
  key: string
  sourceIndex: number
  content_md: string
  original_content_md: string
  question_type: QuestionType
  subject: string
  chapter: string
  difficulty: Difficulty | null
  options: ChoiceOptionDraft[]
  blanks: BlankAnswerDraft[]
  correct_label: string
  has_figure: boolean
  warnings: string[]
  incomplete: boolean
  structureEdited: boolean
  selected: boolean
  saveError: string
  savedQuestion: Question | null
}

export interface SavedImageQuestion {
  question: Question
  taskId: number
}

export interface GeneratedImageTask {
  questionId: number
  taskIds: number[]
}

const CIRCLED_NUMBERS = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩']

export function circledIndex(index: number): string {
  return CIRCLED_NUMBERS[index - 1] ?? `(${index})`
}

function toOptionDrafts(question: ExtractedImageQuestion): ChoiceOptionDraft[] {
  return (question.options ?? []).map((option) => createChoiceOption(option.content_md))
}

function toBlankDrafts(question: ExtractedImageQuestion): BlankAnswerDraft[] {
  return (question.blanks ?? []).map((blank) => createBlankAnswer(blank.answer_md))
}

export function firstDetectedSubject(result: ImageExtractionResult): string {
  return result.questions.map((question) => question.subject?.trim() ?? '').find(Boolean) ?? ''
}

export function createImageItemDrafts(result: ImageExtractionResult): ImageItemDraft[] {
  return result.questions.map((question, position) => ({
    key: `image-item-${question.index}-${position}`,
    sourceIndex: question.index,
    content_md: question.content_md,
    original_content_md: question.content_md,
    question_type: question.question_type,
    subject: question.subject?.trim() ?? '',
    chapter: question.chapter?.trim() ?? '',
    difficulty: question.difficulty ?? null,
    options: toOptionDrafts(question),
    blanks: toBlankDrafts(question),
    correct_label: '',
    has_figure: question.has_figure,
    warnings: [...question.warnings],
    incomplete: question.incomplete === true,
    structureEdited: false,
    selected: question.incomplete !== true,
    saveError: '',
    savedQuestion: null,
  }))
}

export function isImageItemEdited(item: ImageItemDraft): boolean {
  return item.content_md !== item.original_content_md
}

export function canSelectImageItem(item: ImageItemDraft): boolean {
  if (!item.incomplete) return true
  if (isImageItemEdited(item)) return true

  // 用户动过结构且校验通过才算处理过；解答题没有结构可补，仍要求核对题干。
  return (
    item.structureEdited &&
    item.question_type !== 'solve' &&
    validateImageItem(item) === null
  )
}

export function imageItemLockHint(item: ImageItemDraft): string {
  if (item.question_type === 'blank') {
    const missing = item.blanks.filter((blank) => !blank.answer_md.trim()).length
    if (countBlankMarkers(item.content_md) > 0 && missing > 0) {
      return `还有 ${missing} 个空位答案待补全，补全后可勾选保存。`
    }
    if (validateImageItem(item) === null) {
      return '结构已完整；核对并修改任一空位答案后可勾选保存。'
    }
    return '请先修正题干中的 ___ 标记或空位答案。'
  }
  if (item.question_type === 'choice') {
    if (validateImageItem(item) === null) {
      return '结构已完整；核对并修改任一选项后可勾选保存。'
    }
    return '补全选项内容后可勾选保存。'
  }
  return '核对并编辑题干后可勾选保存。'
}

export function visibleImageItemWarnings(item: ImageItemDraft): string[] {
  if (item.question_type === 'blank' && validateImageItem(item) === null) {
    return item.warnings.filter((warning) => !/空位.*(?:没有答案|答案缺失)/.test(warning))
  }
  return item.warnings
}

export function toggleImageSelection(
  selected: readonly number[],
  questionId: number,
  value: unknown,
): number[] {
  if (value !== true) return selected.filter((id) => id !== questionId)
  if (selected.includes(questionId)) return [...selected]
  return [...selected, questionId]
}

export function ensureItemStructure(item: ImageItemDraft): void {
  if (item.question_type === 'choice' && item.options.length < 2) {
    item.options = createDefaultChoiceOptions()
  }
  if (item.question_type === 'blank') {
    item.blanks = syncBlankAnswers(item.content_md, item.blanks)
  }
}

export function validateImageItem(item: ImageItemDraft): string | null {
  if (!item.content_md.trim()) return '题干不能为空'
  if (item.content_md.length > MAX_IMAGE_CONTENT_LENGTH) {
    return `题干不能超过 ${MAX_IMAGE_CONTENT_LENGTH} 个字符`
  }
  if (item.question_type === 'choice') {
    return validateChoiceOptions(item.options)
  }
  if (item.question_type === 'blank') {
    return validateBlankAnswers(item.content_md, item.blanks)
  }
  return null
}

export function toImageQuestionPayload(
  item: ImageItemDraft,
  subject: string,
  imagePath: string,
): QuestionCreate {
  const payload: QuestionCreate = {
    subject: subject.trim(),
    source_type: 'image',
    question_type: item.question_type,
    content_md: item.content_md.trim(),
    answer_md:
      item.question_type === 'choice' && item.correct_label ? `选 ${item.correct_label}` : null,
    explanation_md: null,
    tags: [],
    image_path: imagePath,
  }

  if (item.question_type === 'choice') {
    payload.options = toChoiceOptions(item.options)
  } else if (item.question_type === 'blank') {
    payload.blanks = toBlankAnswers(item.blanks)
  }

  return payload
}
