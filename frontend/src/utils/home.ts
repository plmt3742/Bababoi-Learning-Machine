import type { Draft, StatsOverview } from '../api/types'
import { formatAccuracy, summarizeTrend } from './stats'

export interface HomeKpi {
  label: string
  value: string
  hint: string
}

const dateFormatter = new Intl.DateTimeFormat('zh-CN', {
  month: 'long',
  day: 'numeric',
})

const weekdayFormatter = new Intl.DateTimeFormat('zh-CN', {
  weekday: 'long',
})

function countLabel(value: number | null): string {
  return value === null ? '—' : String(value)
}

function questionHint(stats: StatsOverview | null, questionTotal: number | null): string {
  if (stats) return `相似题 ${stats.total_generated_questions} 道`
  if (questionTotal !== null) return '来自错题本 · 统计暂不可用'
  return '统计暂不可用'
}

function practiceHint(stats: StatsOverview | null, practiceTotal: number | null): string {
  if (stats) return `近 7 天 ${summarizeTrend(stats.recent_trend).practiceCount} 次`
  if (practiceTotal !== null) return '来自练习记录 · 统计暂不可用'
  return '统计暂不可用'
}

function accuracyHint(stats: StatsOverview | null): string {
  if (!stats) return '统计暂不可用'
  if (stats.total_practice_records > 0) return `累计 ${stats.total_practice_records} 次练习`
  return '完成练习后开始统计'
}

function masteryHint(stats: StatsOverview | null): string {
  if (!stats) return '统计暂不可用'
  return `复习 ${stats.reviewing_count} · 未掌握 ${stats.unmastered_count}`
}

/**
 * Build the four overview KPIs. When `/stats/overview` is unavailable the
 * cards keep the counts that can be derived from the question and practice
 * list totals, and show an em dash rather than inventing a value.
 */
export function buildHomeKpis(
  stats: StatsOverview | null,
  questionTotal: number | null,
  practiceTotal: number | null,
): HomeKpi[] {
  return [
    {
      label: '错题总数',
      value: stats ? String(stats.total_questions) : countLabel(questionTotal),
      hint: questionHint(stats, questionTotal),
    },
    {
      label: '练习次数',
      value: stats ? String(stats.total_practice_records) : countLabel(practiceTotal),
      hint: practiceHint(stats, practiceTotal),
    },
    {
      label: '正确率',
      value: stats ? formatAccuracy(stats.accuracy, stats.total_practice_records) : '—',
      hint: accuracyHint(stats),
    },
    {
      label: '已掌握',
      value: stats ? String(stats.mastered_count) : '—',
      hint: masteryHint(stats),
    },
  ]
}

/** `11月6日 星期五` in the browser's locale. */
export function formatHomeDate(date: Date): string {
  return `${dateFormatter.format(date)} ${weekdayFormatter.format(date)}`
}

/** Short, safe excerpt of a saved draft for the resume bar. */
export function draftSummary(draft: Draft | null): string {
  if (!draft) return '有未完成的录入草稿'

  const rawContent = draft.content.content_md
  if (typeof rawContent === 'string') {
    const compact = rawContent.replace(/\s+/g, ' ').trim()
    if (compact) return compact.length > 72 ? `${compact.slice(0, 72)}…` : compact
  }

  const rawSubject = draft.content.subject
  if (typeof rawSubject === 'string' && rawSubject.trim()) {
    return `${rawSubject.trim()} · 未完成的录入草稿`
  }

  return '有未完成的录入草稿'
}

export function sectionErrorText(error: { message: string; code: string } | null): string {
  if (!error) return ''
  return error.code ? `${error.message}（${error.code}）` : error.message
}
