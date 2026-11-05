import type { Difficulty, MasteryStatus, QuestionType, ValidationStatus } from '../api/types'

const QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
  choice: '选择题',
  blank: '填空题',
  solve: '解答题',
}

const MASTERY_STATUS_LABELS: Record<MasteryStatus, string> = {
  unmastered: '未掌握',
  reviewing: '复习中',
  mastered: '已掌握',
}

const MASTERY_STATUS_COLORS: Record<MasteryStatus, string> = {
  unmastered: 'red',
  reviewing: 'orange',
  mastered: 'green',
}

const DIFFICULTY_LABELS: Record<Difficulty, string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
}

const DIFFICULTY_COLORS: Record<Difficulty, string> = {
  easy: 'green',
  medium: 'orange',
  hard: 'red',
}

const VALIDATION_STATUS_LABELS: Record<ValidationStatus, string> = {
  valid: '已校验',
  fallback: '降级生成',
  invalid: '未通过校验',
}

export function questionTypeLabel(type: QuestionType | null | undefined): string {
  return type ? QUESTION_TYPE_LABELS[type] : '解答题'
}

export function masteryStatusLabel(status: MasteryStatus): string {
  return MASTERY_STATUS_LABELS[status]
}

export function masteryStatusColor(status: MasteryStatus): string {
  return MASTERY_STATUS_COLORS[status]
}

export function difficultyLabel(difficulty: Difficulty | null | undefined): string {
  return difficulty ? DIFFICULTY_LABELS[difficulty] : '未标注'
}

export function difficultyColor(difficulty: Difficulty | null | undefined): string {
  return difficulty ? DIFFICULTY_COLORS[difficulty] : 'gray'
}

export function validationStatusLabel(status: ValidationStatus): string {
  return VALIDATION_STATUS_LABELS[status]
}

function toDate(value: string): Date | null {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDate(value: string): string {
  const date = toDate(value)
  if (!date) return value

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
}

export function formatDateTime(value: string): string {
  const date = toDate(value)
  if (!date) return value

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}
