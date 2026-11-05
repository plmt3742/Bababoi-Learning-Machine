import type { GeneratedQuestion, MasteryStatus, QuestionType } from '../api/types'

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
