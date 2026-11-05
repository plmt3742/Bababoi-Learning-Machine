import { computed, onScopeDispose, ref, toValue, watch } from 'vue'
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue'
import { listTasks } from '../api/tasks'
import { normalizeApiError } from '../api/errors'
import type { ApiError } from '../api/errors'
import type { Task, TaskListQuery } from '../api/types'
import { hasActiveTasks } from '../utils/task'

export const DEFAULT_TASK_POLL_INTERVAL_MS = 1500
export const DEFAULT_TASK_POLL_TIMEOUT_MS = 120_000

export type TaskPollingState = 'idle' | 'polling' | 'settled' | 'stopped' | 'timed-out' | 'error'

export interface UseTaskPollingOptions {
  /** Omit to poll the account-wide task list (task center). */
  questionId?: MaybeRefOrGetter<number | null | undefined>
  intervalMs?: number
  timeoutMs?: number
}

export interface TaskPollingController {
  tasks: Ref<Task[]>
  state: Ref<TaskPollingState>
  polling: ComputedRef<boolean>
  loading: Ref<boolean>
  timedOut: ComputedRef<boolean>
  stopped: ComputedRef<boolean>
  error: Ref<ApiError | null>
  lastUpdatedAt: Ref<Date | null>
  /** Seed the list from a detail response so progress renders without an extra round trip. */
  setTasks: (next: Task[]) => void
  start: () => void
  stop: () => void
  refresh: () => Promise<Task[] | null>
  reset: () => void
}

/**
 * Polls GET /tasks while any task is queued/running.
 *
 * - one request at a time; a slow response never stacks another poll on top
 * - stops itself when every task is terminal, after a manual stop, or on error
 * - pauses after `timeoutMs` with a `timed-out` state so the caller can show a warning
 * - increments a request token on reset/unmount so late responses are ignored
 */
export function useTaskPolling(options: UseTaskPollingOptions = {}): TaskPollingController {
  const intervalMs = Math.max(300, options.intervalMs ?? DEFAULT_TASK_POLL_INTERVAL_MS)
  const timeoutMs = Math.max(intervalMs, options.timeoutMs ?? DEFAULT_TASK_POLL_TIMEOUT_MS)

  const tasks = ref<Task[]>([])
  const state = ref<TaskPollingState>('idle')
  const loading = ref(false)
  const error = ref<ApiError | null>(null)
  const lastUpdatedAt = ref<Date | null>(null)

  const polling = computed(() => state.value === 'polling')
  const timedOut = computed(() => state.value === 'timed-out')
  const stopped = computed(() => state.value === 'stopped')

  let timer: ReturnType<typeof setTimeout> | null = null
  let requestId = 0
  let inFlight = false
  let startedAt = 0
  let disposed = false

  function clearTimer(): void {
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
  }

  function halt(next: TaskPollingState): void {
    clearTimer()
    state.value = next
  }

  function buildQuery(): TaskListQuery {
    const params: TaskListQuery = {}
    const questionId = toValue(options.questionId)

    if (typeof questionId === 'number' && questionId > 0) {
      params.question_id = questionId
    }

    return params
  }

  async function fetchTasks(): Promise<Task[] | null> {
    // Overlapping requests would race each other into the same list.
    if (disposed || inFlight) return null

    const currentId = ++requestId
    inFlight = true
    loading.value = true

    try {
      const response = await listTasks(buildQuery())
      if (disposed || currentId !== requestId) return null

      tasks.value = response.items
      error.value = null
      lastUpdatedAt.value = new Date()
      return response.items
    } catch (cause) {
      if (disposed || currentId !== requestId) return null

      error.value = normalizeApiError(cause)
      halt('error')
      return null
    } finally {
      if (currentId === requestId) {
        inFlight = false
        loading.value = false
      }
    }
  }

  function scheduleNextTick(): void {
    clearTimer()
    if (disposed || state.value !== 'polling') return

    timer = setTimeout(() => {
      void tick()
    }, intervalMs)
  }

  async function tick(): Promise<void> {
    timer = null
    if (disposed || state.value !== 'polling') return

    const result = await fetchTasks()
    if (result === null) return
    if (disposed || state.value !== 'polling') return

    if (!hasActiveTasks(result)) {
      halt('settled')
      return
    }

    if (Date.now() - startedAt >= timeoutMs) {
      halt('timed-out')
      return
    }

    scheduleNextTick()
  }

  function start(): void {
    if (disposed || state.value === 'polling') return

    error.value = null
    state.value = 'polling'
    startedAt = Date.now()
    void tick()
  }

  function stop(): void {
    if (state.value !== 'polling') {
      clearTimer()
      return
    }

    halt('stopped')
  }

  async function refresh(): Promise<Task[] | null> {
    const result = await fetchTasks()
    if (result === null || disposed) return null

    if (hasActiveTasks(result)) {
      if (state.value !== 'polling') {
        state.value = 'polling'
        startedAt = Date.now()
        scheduleNextTick()
      }
    } else {
      halt('settled')
    }

    return result
  }

  function setTasks(next: Task[]): void {
    if (disposed) return
    tasks.value = next
    lastUpdatedAt.value = new Date()
  }

  function reset(): void {
    clearTimer()
    requestId += 1
    inFlight = false
    loading.value = false
    tasks.value = []
    state.value = 'idle'
    error.value = null
    lastUpdatedAt.value = null
    startedAt = 0
  }

  if (options.questionId !== undefined) {
    watch(
      () => toValue(options.questionId),
      () => reset(),
    )
  }

  onScopeDispose(() => {
    disposed = true
    clearTimer()
    requestId += 1
    inFlight = false
    state.value = 'idle'
  })

  return {
    tasks,
    state,
    polling,
    loading,
    timedOut,
    stopped,
    error,
    lastUpdatedAt,
    setTasks,
    start,
    stop,
    refresh,
    reset,
  }
}
