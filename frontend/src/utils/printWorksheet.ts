/**
 * Print worksheet helpers (issue #109 / plan F-7).
 *
 * The worksheet is built client-side from the existing list + detail APIs:
 * one filtered list request, then bounded-concurrency detail requests. These
 * helpers stay pure so the query hand-off and the concurrency scheduling can be
 * unit tested without mounting a view.
 */

/** Hard cap on how many questions one printed sheet may contain. */
export const PRINT_LIMIT = 20

/** List page size; the backend caps `page_size` at 100, so this is one request. */
export const PRINT_PAGE_SIZE = 100

/** Detail requests in flight at the same time. */
export const PRINT_CONCURRENCY = 3

export interface PrintFilterInput {
  q?: string | null
  subject?: string | null
  tag?: string | null
  mastery_status?: string | null
}

/**
 * Convert the list page filters into the print route query.
 *
 * Empty values are dropped and `page` is never carried over: a worksheet is a
 * single flat run of the current filter, not a paged view.
 */
export function buildPrintQuery(filters: PrintFilterInput): Record<string, string> {
  const query: Record<string, string> = {}

  const q = filters.q?.trim()
  const subject = filters.subject?.trim()
  const tag = filters.tag?.trim()
  const masteryStatus = filters.mastery_status?.trim()

  if (q) query.q = q
  if (subject) query.subject = subject
  if (tag) query.tag = tag
  if (masteryStatus) query.mastery_status = masteryStatus

  return query
}

/**
 * Run `worker` over `items` with at most `limit` promises in flight.
 *
 * The result array keeps the input order and mirrors `Promise.allSettled`: one
 * rejected item never aborts the rest. Used for the per-question detail fetch so
 * a single failing question degrades to a placeholder instead of blanking the
 * whole sheet.
 */
export async function settleWithConcurrency<T, R>(
  items: readonly T[],
  limit: number,
  worker: (item: T, index: number) => Promise<R>,
): Promise<PromiseSettledResult<R>[]> {
  const results: PromiseSettledResult<R>[] = new Array(items.length)
  const workerCount = Math.min(Math.max(1, Math.floor(limit)), items.length)
  if (workerCount === 0) return results

  let nextIndex = 0

  async function run(): Promise<void> {
    while (nextIndex < items.length) {
      const index = nextIndex
      nextIndex += 1

      try {
        results[index] = { status: 'fulfilled', value: await worker(items[index], index) }
      } catch (reason) {
        results[index] = { status: 'rejected', reason }
      }
    }
  }

  await Promise.all(Array.from({ length: workerCount }, () => run()))
  return results
}
