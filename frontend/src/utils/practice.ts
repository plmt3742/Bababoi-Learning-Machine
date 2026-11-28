import type {
  GeneratedQuestion,
  MasteryStatus,
  PracticeDueReason,
  QuestionType,
} from '../api/types'
import { parseApiTime } from './time'

export interface PracticeAnswerDraft {
  choice: string
  blanks: string[]
  solve: string
}

export interface PracticeResultItem {
  generated_question_id: number
  user_answer: string | null
  is_correct: boolean
  duration_seconds: number
}

/** Route params may be a string or string[]; only canonical positive integers pass. */
export function parsePracticeId(value: unknown): number | null {
  if (typeof value !== 'string') return null

  const parsed = Number.parseInt(value, 10)
  if (!Number.isFinite(parsed) || parsed <= 0) return null

  return String(parsed) === value ? parsed : null
}

/**
 * Generated questions occasionally omit a type or ship unusable options.
 * Fall back to the shape of the payload so the practice card always renders.
 */
export function resolvePracticeQuestionType(
  question: Pick<GeneratedQuestion, 'question_type' | 'options' | 'blanks'>,
): QuestionType {
  if (question.question_type === 'choice' && (question.options?.length ?? 0) > 0) return 'choice'
  if (question.question_type === 'blank') return 'blank'
  if (question.question_type === 'solve') return 'solve'
  if ((question.options?.length ?? 0) > 0) return 'choice'
  if ((question.blanks?.length ?? 0) > 0) return 'blank'
  return 'solve'
}

export function blankAnswerCount(question: Pick<GeneratedQuestion, 'blanks'>): number {
  return Math.max(1, question.blanks?.length ?? 0)
}

const CHOICE_LABEL_PREFIX = /^(?:选\s*|答案[：:]?\s*|故选\s*|选项\s*)?([A-F])(?=$|[\s.。，,、:：)）])/i

/** Pull the single-choice letter out of an answer like `选 A`, `答案：B`, or `**C**`. */
export function extractChoiceAnswerLabel(answerMd: string | null | undefined): string {
  if (!answerMd) return ''
  const cleaned = answerMd.replace(/[*_`$]/g, '').trim()
  const match = CHOICE_LABEL_PREFIX.exec(cleaned)
  return match ? match[1].toUpperCase() : ''
}

export function buildPracticeUserAnswer(
  type: QuestionType,
  draft: PracticeAnswerDraft,
): string | null {
  if (type === 'choice') {
    const choice = draft.choice.trim()
    return choice || null
  }

  if (type === 'blank') {
    const values = draft.blanks.map((value) => value.trim())
    return values.some((value) => value.length > 0) ? values.join('；') : null
  }

  const answer = draft.solve.trim()
  return answer || null
}

export function capPracticeDuration(seconds: number): number {
  if (!Number.isFinite(seconds)) return 0
  return Math.max(0, Math.min(3600, Math.floor(seconds)))
}

/** `mm:ss`, or `h:mm:ss` when a practice round runs longer than an hour. */
export function formatPracticeDuration(seconds: number): string {
  const safe = Math.max(0, Math.floor(Number.isFinite(seconds) ? seconds : 0))
  const hours = Math.floor(safe / 3600)
  const minutes = Math.floor((safe % 3600) / 60)
  const rest = safe % 60

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
  }

  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

/** Per-question timers stop at the backend's 3600-second ceiling. */
export function formatPracticeClock(seconds: number): string {
  return formatPracticeDuration(capPracticeDuration(seconds))
}

export function calculateAccuracy(correct: number, total: number): number {
  if (total <= 0) return 0
  return Math.round((correct / total) * 100)
}

/** Aggregate self-grades into the parent question's mastery status. */
export function masteryStatusForResults(
  results: ReadonlyArray<{ is_correct: boolean }>,
): MasteryStatus {
  if (results.length === 0) return 'unmastered'

  const correct = results.filter((item) => item.is_correct).length
  if (correct === results.length) return 'mastered'
  if (correct === 0) return 'unmastered'
  return 'reviewing'
}

export const DUE_REVIEW_DAYS: Record<MasteryStatus, number> = {
  unmastered: 1,
  reviewing: 3,
  mastered: 7,
}

const DUE_REASON_BY_STATUS: Record<MasteryStatus, PracticeDueReason> = {
  unmastered: 'unmastered_1d',
  reviewing: 'reviewing_3d',
  mastered: 'mastered_7d',
}

export function resolveDueReason(
  mastery: MasteryStatus,
  lastPracticedAt: string | null | undefined,
  now: Date = new Date(),
): PracticeDueReason | null {
  if (!lastPracticedAt) return 'never'

  const last = parseApiTime(lastPracticedAt)
  if (Number.isNaN(last.getTime())) return 'never'

  const days = (now.getTime() - last.getTime()) / 86_400_000
  return days >= DUE_REVIEW_DAYS[mastery] ? DUE_REASON_BY_STATUS[mastery] : null
}

export function dueReasonLabel(reason: PracticeDueReason): string {
  switch (reason) {
    case 'never':
      return '还没练过'
    case 'unmastered_1d':
      return '已隔 1 天'
    case 'reviewing_3d':
      return '已隔 3 天'
    case 'mastered_7d':
      return '已隔 7 天'
  }
}

export type PracticeShortcut =
  | { type: 'choice'; label: string }
  | { type: 'reveal' }
  | { type: 'grade'; correct: boolean }

export interface PracticeShortcutInput {
  key: string
  code: string
  revealed: boolean
  submitting: boolean
  choiceLabels: string[]
  editable: boolean
  activatable: boolean
  defaultPrevented?: boolean
  metaKey?: boolean
  ctrlKey?: boolean
  altKey?: boolean
}

export function resolvePracticeShortcut(
  input: PracticeShortcutInput,
): PracticeShortcut | null {
  if (input.defaultPrevented || input.metaKey || input.ctrlKey || input.altKey) return null
  if (input.editable) return null
  if (input.activatable && (input.key === ' ' || input.key === 'Enter')) return null

  if (!input.revealed && /^[a-f]$/i.test(input.key)) {
    const label = input.key.toUpperCase()
    if (input.choiceLabels.includes(label)) return { type: 'choice', label }
  }

  if (input.code === 'Space') return { type: 'reveal' }

  if (input.revealed && !input.submitting) {
    if (input.key === '1') return { type: 'grade', correct: false }
    if (input.key === '2') return { type: 'grade', correct: true }
  }

  return null
}
