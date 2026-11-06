/**
 * FE-018 draft helpers.
 *
 * Server drafts are account-level (`/drafts/me`) and local drafts are the
 * offline/crash fallback. Both carry the same editor snapshot; this module owns
 * the shape, the localStorage record, timestamp comparison and the "is this
 * worth restoring?" rules so the view and the composable stay dumb.
 */
import type { Draft, QuestionType } from '../api/types'

export const MAX_DRAFT_TAGS = 10
export const MAX_DRAFT_OPTIONS = 6
export const MAX_DRAFT_BLANKS = 20

export interface DraftChoiceOption {
  content_md: string
}

export interface DraftBlankAnswer {
  answer_md: string
}

/** Full editor snapshot needed to restore `/questions/new` in text mode. */
export interface QuestionDraftContent {
  subject: string
  chapter: string
  question_type: QuestionType
  content_md: string
  answer_md: string
  explanation_md: string
  tags: string[]
  options: DraftChoiceOption[]
  blanks: DraftBlankAnswer[]
  choice_correct_label: string
}

/** localStorage record, keyed per user: `bababoi:draft:{userId}`. */
export interface LocalDraftRecord {
  content: QuestionDraftContent
  client_updated_at: string
  server_version: number | null
}

export interface DraftCandidate {
  content: QuestionDraftContent
  updatedAt: string
  source: 'local' | 'server'
  version: number | null
}

const DRAFT_KEY_PREFIX = 'bababoi:draft:'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function readString(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function readQuestionType(value: unknown): QuestionType {
  if (value === 'choice' || value === 'blank') return value
  return 'solve'
}

/** Defensive parser for unknown server/local JSON; never throws. */
export function normalizeDraftContent(raw: Record<string, unknown>): QuestionDraftContent {
  const rawLabel = readString(raw.choice_correct_label).trim().toUpperCase()

  return {
    subject: readString(raw.subject),
    chapter: readString(raw.chapter),
    question_type: readQuestionType(raw.question_type),
    content_md: readString(raw.content_md),
    answer_md: readString(raw.answer_md),
    explanation_md: readString(raw.explanation_md),
    tags: Array.isArray(raw.tags)
      ? raw.tags
          .filter((tag): tag is string => typeof tag === 'string')
          .map((tag) => tag.trim())
          .filter((tag) => tag.length > 0)
          .slice(0, MAX_DRAFT_TAGS)
      : [],
    options: Array.isArray(raw.options)
      ? raw.options.slice(0, MAX_DRAFT_OPTIONS).map((option) => ({
          content_md: isRecord(option) ? readString(option.content_md) : '',
        }))
      : [],
    blanks: Array.isArray(raw.blanks)
      ? raw.blanks.slice(0, MAX_DRAFT_BLANKS).map((blank) => ({
          answer_md: isRecord(blank) ? readString(blank.answer_md) : '',
        }))
      : [],
    choice_correct_label: /^[A-F]$/.test(rawLabel) ? rawLabel : '',
  }
}

/**
 * A draft is worth restoring when it contains question work, not just a subject
 * the user happened to pick before navigating away.
 */
export function hasMeaningfulDraftContent(content: QuestionDraftContent): boolean {
  return (
    content.content_md.trim().length > 0 ||
    content.answer_md.trim().length > 0 ||
    content.explanation_md.trim().length > 0 ||
    content.tags.length > 0 ||
    content.options.some((option) => option.content_md.trim().length > 0) ||
    content.blanks.some((blank) => blank.answer_md.trim().length > 0)
  )
}

/** Stable comparison key; used for dirty checks and "differs from form". */
export function draftContentKey(content: QuestionDraftContent): string {
  return JSON.stringify([
    content.subject,
    content.chapter,
    content.question_type,
    content.content_md,
    content.answer_md,
    content.explanation_md,
    content.tags,
    content.options.map((option) => option.content_md),
    content.blanks.map((blank) => blank.answer_md),
    content.choice_correct_label,
  ])
}

export function draftStorageKey(userId: number): string {
  return `${DRAFT_KEY_PREFIX}${userId}`
}

function getLocalStorage(): Storage | null {
  if (typeof window === 'undefined') return null

  try {
    return window.localStorage
  } catch {
    return null
  }
}

export function readLocalDraft(userId: number): LocalDraftRecord | null {
  const storage = getLocalStorage()
  if (!storage) return null

  try {
    const raw = storage.getItem(draftStorageKey(userId))
    if (!raw) return null

    const parsed: unknown = JSON.parse(raw)
    if (!isRecord(parsed) || !isRecord(parsed.content)) return null

    const clientUpdatedAt = readString(parsed.client_updated_at)
    if (!clientUpdatedAt) return null

    return {
      content: normalizeDraftContent(parsed.content),
      client_updated_at: clientUpdatedAt,
      server_version: typeof parsed.server_version === 'number' ? parsed.server_version : null,
    }
  } catch {
    return null
  }
}

export function writeLocalDraft(userId: number, record: LocalDraftRecord): boolean {
  const storage = getLocalStorage()
  if (!storage) return false

  try {
    storage.setItem(draftStorageKey(userId), JSON.stringify(record))
    return true
  } catch {
    // Quota exceeded / storage disabled: the server draft is the fallback.
    return false
  }
}

export function clearLocalDraft(userId: number): void {
  const storage = getLocalStorage()
  if (!storage) return

  try {
    storage.removeItem(draftStorageKey(userId))
  } catch {
    // Ignore storage failures on cleanup.
  }
}

function parseTimestamp(value: string): number | null {
  const time = Date.parse(value)
  return Number.isNaN(time) ? null : time
}

/**
 * Pick the freshest draft; a tie or invalid local timestamp prefers the server,
 * per `docs/product/06-draft-dual-write.md` §5.
 */
export function chooseDraftCandidate(
  local: LocalDraftRecord | null,
  server: Draft | null,
): DraftCandidate | null {
  const localTime = local ? parseTimestamp(local.client_updated_at) : null
  const serverTime = server ? parseTimestamp(server.updated_at) : null

  if (server && (localTime === null || (serverTime !== null && serverTime >= localTime))) {
    return {
      content: normalizeDraftContent(server.content),
      updatedAt: server.updated_at,
      source: 'server',
      version: server.version,
    }
  }

  if (local) {
    return {
      content: local.content,
      updatedAt: local.client_updated_at,
      source: 'local',
      version: server?.version ?? local.server_version,
    }
  }

  return null
}

/** `HH:mm` used by the save status line; invalid timestamps render empty. */
export function formatDraftClockTime(value: string | Date): string {
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return ''

  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${hours}:${minutes}`
}
