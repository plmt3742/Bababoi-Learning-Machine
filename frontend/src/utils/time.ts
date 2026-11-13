/**
 * 后端时间有两套序列化口径，前端必须都按 UTC 解析：
 *
 * - `drafts` / `stats` 在路由层补了时区，返回 `2026-11-11T10:43:58Z`；
 * - `questions` / `tasks` / `practice-records` / `auth.me` / `settings.preferences`
 *   落库是 UTC naive（`app/db/base.py` 的 `utcnow()` 明确去掉了 tzinfo），
 *   序列化出来是 `2026-11-11T10:43:58`，没有后缀。
 *
 * `new Date('2026-11-11T10:43:58')` 会按**浏览器本地时区**解析，
 * 在 UTC+8 的机器上直接把 UTC 的钟点当成本地时间显示，差 8 小时。
 * 这里只给「日期 + 时间、但没有时区」的串补 `Z`；纯日期（`2026-11-11`）
 * 按规范本来就是 UTC，补 `Z` 会变成非法值，所以原样交给 Date。
 */
const NAIVE_DATE_TIME = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/

export function parseApiTime(value: string): Date {
  const trimmed = value.trim()
  if (!NAIVE_DATE_TIME.test(trimmed)) return new Date(trimmed)
  return new Date(`${trimmed.replace(' ', 'T')}Z`)
}

export function parseApiTimeOrNull(value: string | null | undefined): Date | null {
  if (!value) return null
  const date = parseApiTime(value)
  return Number.isNaN(date.getTime()) ? null : date
}
