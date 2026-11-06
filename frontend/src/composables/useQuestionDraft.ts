import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import { getDraft, removeDraft, saveDraft } from '../api/drafts'
import { normalizeApiError } from '../api/errors'
import type { ApiError } from '../api/errors'
import type { Draft } from '../api/types'
import {
  chooseDraftCandidate,
  clearLocalDraft,
  draftContentKey,
  hasMeaningfulDraftContent,
  normalizeDraftContent,
  readLocalDraft,
  writeLocalDraft,
} from '../utils/draft'
import type { DraftCandidate, QuestionDraftContent } from '../utils/draft'

export const DRAFT_LOCAL_DEBOUNCE_MS = 400
export const DRAFT_SERVER_DEBOUNCE_MS = 5000
const DRAFT_DELETE_WAIT_MS = 3000

export type DraftStatus =
  'idle' | 'pending' | 'saving' | 'saved' | 'local-only' | 'error' | 'conflict'

type DraftFailureKind = 'save' | 'delete' | 'local' | null

export interface UseQuestionDraftOptions {
  /** Reactive snapshot getter for the text-mode editor. */
  content: () => QuestionDraftContent
  userId: () => number | null
  /** Called only when the user explicitly restores a draft. */
  applyContent: (content: QuestionDraftContent) => void
  enabled?: () => boolean
  localDebounceMs?: number
  serverDebounceMs?: number
}

export interface QuestionDraftController {
  status: Ref<DraftStatus>
  savedAt: Ref<Date | null>
  errorMessage: Ref<string>
  conflict: Ref<Draft | null>
  candidate: Ref<DraftCandidate | null>
  candidateVisible: Ref<boolean>
  hasHiddenCandidate: ComputedRef<boolean>
  hasDraft: ComputedRef<boolean>
  blockedReason: ComputedRef<string>
  loading: Ref<boolean>
  resolvingConflict: Ref<boolean>
  busy: ComputedRef<boolean>
  load: () => Promise<void>
  restore: () => void
  dismissRestore: () => void
  showRestore: () => void
  discard: () => Promise<void>
  retry: () => Promise<void>
  resolveConflict: (choice: 'local' | 'server') => Promise<void>
  prepareSubmit: () => void
  cancelSubmit: () => void
  clearAfterSubmit: () => Promise<void>
}

function toDate(value: string): Date | null {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

/**
 * Dual-write draft state for the text mode of `/questions/new`.
 *
 * - localStorage debounced ~400ms; server PUT debounced ~5s
 * - restoring is always user-initiated; the form is never overwritten silently
 * - while a restore candidate or a 409 is unresolved, server writes pause but
 *   local writes continue, so both versions stay available
 * - submit clears local + server; unmount flushes local and starts a final
 *   server save without awaiting it
 */
export function useQuestionDraft(options: UseQuestionDraftOptions): QuestionDraftController {
  const localDebounceMs = Math.max(200, options.localDebounceMs ?? DRAFT_LOCAL_DEBOUNCE_MS)
  const serverDebounceMs = Math.max(1000, options.serverDebounceMs ?? DRAFT_SERVER_DEBOUNCE_MS)

  const status = ref<DraftStatus>('idle')
  const savedAt = ref<Date | null>(null)
  const errorMessage = ref('')
  const conflict = ref<Draft | null>(null)
  const candidate = ref<DraftCandidate | null>(null)
  const candidateVisible = ref(false)
  const loading = ref(false)
  const resolvingConflict = ref(false)
  const serverVersion = ref<number | null>(null)
  const hasLocalRecord = ref(false)
  const failureKind = ref<DraftFailureKind>(null)

  const hasHiddenCandidate = computed(() => candidate.value !== null && !candidateVisible.value)
  const hasDraft = computed(
    () => candidate.value !== null || serverVersion.value !== null || hasLocalRecord.value,
  )
  const blockedReason = computed(() => {
    if (conflict.value) return '草稿冲突待处理，暂不同步服务端'
    if (candidate.value) return '未完成草稿待处理，暂不同步服务端'
    return ''
  })
  const busy = computed(
    () => status.value === 'saving' || status.value === 'pending' || resolvingConflict.value,
  )

  let localTimer: ReturnType<typeof setTimeout> | null = null
  let serverTimer: ReturnType<typeof setTimeout> | null = null
  let inFlight: Promise<boolean> | null = null
  let localUpdatedAt = ''
  let lastKey = draftContentKey(options.content())
  let dirty = false
  let loadingRequested = false
  let disposed = false
  let closed = false
  let suspended = false

  function isEnabled(): boolean {
    return options.enabled ? options.enabled() : true
  }

  function cancelLocalTimer(): void {
    if (localTimer !== null) {
      clearTimeout(localTimer)
      localTimer = null
    }
  }

  function cancelServerTimer(): void {
    if (serverTimer !== null) {
      clearTimeout(serverTimer)
      serverTimer = null
    }
  }

  function cancelTimers(): void {
    cancelLocalTimer()
    cancelServerTimer()
  }

  function canSyncServer(): boolean {
    return !disposed && !closed && !suspended && conflict.value === null && candidate.value === null
  }

  function scheduleLocal(delay = localDebounceMs): void {
    cancelLocalTimer()
    if (disposed || closed || suspended) return

    localTimer = setTimeout(() => {
      localTimer = null
      flushLocalNow()
    }, delay)
  }

  function scheduleServer(delay = serverDebounceMs): void {
    cancelServerTimer()
    if (!canSyncServer()) return

    serverTimer = setTimeout(() => {
      serverTimer = null
      void performServerSave()
    }, delay)
  }

  function clearLocalNow(): void {
    const userId = options.userId()
    if (userId !== null) clearLocalDraft(userId)
    hasLocalRecord.value = false
  }

  function flushLocalNow(): void {
    const userId = options.userId()
    if (userId === null) return

    const content = options.content()
    if (!hasMeaningfulDraftContent(content)) {
      clearLocalNow()
      return
    }

    localUpdatedAt = new Date().toISOString()
    const saved = writeLocalDraft(userId, {
      content,
      client_updated_at: localUpdatedAt,
      server_version: serverVersion.value,
    })
    hasLocalRecord.value = saved

    if (saved) {
      if (failureKind.value === 'local') {
        failureKind.value = null
        errorMessage.value = ''
        status.value = 'pending'
      }
      return
    }

    status.value = 'error'
    failureKind.value = 'local'
    errorMessage.value = '本地草稿保存失败，请检查浏览器存储空间'
  }

  async function deleteServerDraft(): Promise<boolean> {
    try {
      await removeDraft()
      serverVersion.value = null
      savedAt.value = null
      if (!dirty) status.value = 'idle'
      return true
    } catch (cause) {
      const apiError = normalizeApiError(cause)
      if (apiError.status === 404) {
        serverVersion.value = null
        return true
      }
      status.value = 'error'
      failureKind.value = 'delete'
      errorMessage.value = '服务端草稿清理失败，请重试'
      return false
    }
  }

  async function loadConflict(apiError: ApiError): Promise<void> {
    errorMessage.value = apiError.message
    failureKind.value = 'save'

    let latest: Draft | null = null
    let readFailed = false

    try {
      latest = await getDraft()
    } catch {
      readFailed = true
    }

    if (disposed) return

    if (readFailed) {
      status.value = 'error'
      errorMessage.value = '草稿版本冲突，且无法读取服务端最新版本，请重试'
      return
    }

    if (!latest) {
      serverVersion.value = null
      status.value = 'error'
      errorMessage.value = '草稿已在其他位置更新，请重试同步'
      return
    }

    conflict.value = latest
    serverVersion.value = latest.version
    status.value = 'conflict'
    errorMessage.value = ''
  }

  async function performServerSave(): Promise<boolean> {
    if (!canSyncServer()) return false

    const pending = inFlight
    if (pending) return pending

    const content = options.content()
    if (!hasMeaningfulDraftContent(content)) {
      flushLocalNow()
      dirty = false
      if (serverVersion.value !== null) return deleteServerDraft()
      status.value = 'idle'
      savedAt.value = null
      return true
    }

    if (!localUpdatedAt) localUpdatedAt = new Date().toISOString()
    const savedKey = draftContentKey(content)
    status.value = 'saving'
    failureKind.value = null

    const request = (async (): Promise<boolean> => {
      try {
        const draft = await saveDraft({
          content: {
            subject: content.subject,
            chapter: content.chapter,
            question_type: content.question_type,
            content_md: content.content_md,
            answer_md: content.answer_md,
            explanation_md: content.explanation_md,
            tags: content.tags,
            options: content.options,
            blanks: content.blanks,
            choice_correct_label: content.choice_correct_label,
          },
          base_version: serverVersion.value,
          client_updated_at: localUpdatedAt,
        })

        if (closed) return true

        serverVersion.value = draft.version
        savedAt.value = toDate(draft.updated_at)
        errorMessage.value = ''
        failureKind.value = null

        const stillDirty = isEnabled() && draftContentKey(options.content()) !== savedKey
        dirty = stillDirty

        if (stillDirty) {
          status.value = 'pending'
          scheduleLocal()
          scheduleServer()
        } else {
          status.value = 'saved'
          const userId = options.userId()
          if (hasLocalRecord.value && userId !== null) {
            writeLocalDraft(userId, {
              content,
              client_updated_at: localUpdatedAt,
              server_version: draft.version,
            })
          }
        }

        return true
      } catch (cause) {
        const apiError = normalizeApiError(cause)

        if (apiError.status === 409 || apiError.code === 'DRAFT_VERSION_CONFLICT') {
          await loadConflict(apiError)
        } else {
          status.value = 'error'
          failureKind.value = 'save'
          errorMessage.value = apiError.message
        }

        return false
      } finally {
        inFlight = null
        if (status.value === 'saving' && !closed) {
          status.value = 'error'
          failureKind.value = 'save'
          if (!errorMessage.value) errorMessage.value = '草稿保存失败，请重试'
        }
      }
    })()

    inFlight = request
    return request
  }

  function handleContentChange(): void {
    if (disposed || closed || suspended || !isEnabled()) return

    const content = options.content()
    const key = draftContentKey(content)
    if (key === lastKey) return

    lastKey = key
    dirty = true
    errorMessage.value = ''
    failureKind.value = null

    // Typing while the restore banner is open counts as "稍后": keep the old
    // candidate available through the small 继续草稿 action.
    if (candidate.value && candidateVisible.value) candidateVisible.value = false

    if (!hasMeaningfulDraftContent(content)) {
      status.value = candidate.value || conflict.value ? 'local-only' : 'pending'
      scheduleLocal()
      if (canSyncServer()) scheduleServer()
      return
    }

    if (candidate.value || conflict.value) {
      status.value = 'local-only'
      scheduleLocal()
      return
    }

    status.value = 'pending'
    scheduleLocal()
    if (canSyncServer()) scheduleServer()
  }

  function restore(): void {
    const chosen = candidate.value
    if (!chosen) return

    candidate.value = null
    candidateVisible.value = false
    options.applyContent(chosen.content)
    lastKey = draftContentKey(options.content())
    dirty = chosen.source === 'local'
    localUpdatedAt = new Date().toISOString()
    serverVersion.value = chosen.version
    savedAt.value = toDate(chosen.updatedAt)
    flushLocalNow()
    errorMessage.value = ''
    failureKind.value = null

    if (chosen.source === 'server') {
      status.value = 'saved'
      return
    }

    status.value = 'pending'
    scheduleServer(0)
  }

  function dismissRestore(): void {
    if (candidate.value) candidateVisible.value = false
  }

  function showRestore(): void {
    if (candidate.value) candidateVisible.value = true
  }

  async function discard(): Promise<void> {
    if (disposed) return

    suspended = true
    cancelTimers()
    candidate.value = null
    candidateVisible.value = false
    conflict.value = null
    clearLocalNow()
    serverVersion.value = null
    savedAt.value = null
    status.value = 'idle'
    errorMessage.value = ''
    failureKind.value = null
    dirty = false

    try {
      await removeDraft()
    } catch (cause) {
      const apiError = normalizeApiError(cause)
      if (apiError.status !== 404) {
        status.value = 'error'
        failureKind.value = 'delete'
        errorMessage.value = '服务端草稿清理失败，请重试'
      }
    } finally {
      suspended = false
      const current = options.content()
      lastKey = draftContentKey(current)

      if (!closed && isEnabled() && hasMeaningfulDraftContent(current)) {
        dirty = true
        status.value = 'pending'
        scheduleLocal(0)
        if (canSyncServer()) scheduleServer(0)
      }
    }
  }

  async function retryDelete(): Promise<void> {
    try {
      await removeDraft()
      serverVersion.value = null
      status.value = 'idle'
      errorMessage.value = ''
      failureKind.value = null
    } catch (cause) {
      status.value = 'error'
      failureKind.value = 'delete'
      errorMessage.value = normalizeApiError(cause).message
    }
  }

  async function retry(): Promise<void> {
    if (failureKind.value === 'delete') {
      await retryDelete()
      return
    }

    if (failureKind.value === 'local') {
      flushLocalNow()
      if (status.value !== 'error') {
        status.value = 'pending'
        if (canSyncServer()) scheduleServer()
      }
      return
    }

    await performServerSave()
  }

  async function resolveConflict(choice: 'local' | 'server'): Promise<void> {
    const serverDraft = conflict.value
    if (!serverDraft || resolvingConflict.value) return

    resolvingConflict.value = true
    errorMessage.value = ''

    try {
      if (choice === 'server') {
        options.applyContent(normalizeDraftContent(serverDraft.content))
        conflict.value = null
        serverVersion.value = serverDraft.version
        savedAt.value = toDate(serverDraft.updated_at)
        lastKey = draftContentKey(options.content())
        dirty = false
        localUpdatedAt = new Date().toISOString()
        flushLocalNow()
        status.value = 'saved'
        failureKind.value = null
        return
      }

      // Keep local: the server version becomes the new optimistic-lock base so
      // the user's input overwrites the remote copy explicitly.
      serverVersion.value = serverDraft.version
      conflict.value = null
      status.value = 'pending'
      await performServerSave()
    } finally {
      resolvingConflict.value = false
    }
  }

  function prepareSubmit(): void {
    suspended = true
    cancelTimers()
    if (dirty) flushLocalNow()
  }

  function cancelSubmit(): void {
    suspended = false
    if (disposed || closed) return

    const current = options.content()
    const key = draftContentKey(current)
    if (key !== lastKey) {
      lastKey = key
      dirty = true
    }
    if (!dirty) return

    if (!hasMeaningfulDraftContent(current)) {
      status.value = 'pending'
      scheduleLocal()
      if (canSyncServer()) scheduleServer()
      return
    }

    status.value = candidate.value || conflict.value ? 'local-only' : 'pending'
    scheduleLocal(0)
    if (canSyncServer()) scheduleServer()
  }

  async function clearAfterSubmit(): Promise<void> {
    closed = true
    suspended = true
    cancelTimers()

    const pending = inFlight
    if (pending) {
      await Promise.race([
        pending.catch(() => false),
        new Promise<boolean>((resolve) => {
          setTimeout(() => resolve(false), DRAFT_DELETE_WAIT_MS)
        }),
      ])
    }

    clearLocalNow()
    candidate.value = null
    candidateVisible.value = false
    conflict.value = null
    serverVersion.value = null
    savedAt.value = null
    status.value = 'idle'
    errorMessage.value = ''
    failureKind.value = null
    dirty = false
    lastKey = draftContentKey(options.content())

    try {
      await removeDraft()
    } catch {
      // Local is already clean; leaving a stale server draft is recoverable.
    }
  }

  async function load(): Promise<void> {
    if (loadingRequested || disposed) return
    loadingRequested = true
    loading.value = true

    const startKey = draftContentKey(options.content())
    const userId = options.userId()
    const local = userId !== null ? readLocalDraft(userId) : null

    if (local) {
      hasLocalRecord.value = true
      localUpdatedAt = local.client_updated_at
    }

    let server: Draft | null = null
    let serverError: ApiError | null = null

    try {
      server = await getDraft()
    } catch (cause) {
      serverError = normalizeApiError(cause)
    }

    if (disposed) return

    serverVersion.value = server
      ? server.version
      : serverError
        ? (local?.server_version ?? null)
        : null

    const chosen = chooseDraftCandidate(local, server)
    const currentKey = draftContentKey(options.content())
    const typedWhileLoading = currentKey !== startKey

    if (
      chosen &&
      hasMeaningfulDraftContent(chosen.content) &&
      draftContentKey(chosen.content) !== currentKey
    ) {
      if (chosen.source === 'local') chosen.version = serverVersion.value
      candidate.value = chosen
      candidateVisible.value = !typedWhileLoading
      savedAt.value = toDate(chosen.updatedAt)
      if (!typedWhileLoading) {
        status.value = chosen.source === 'server' ? 'saved' : 'local-only'
      }
    } else if (!typedWhileLoading) {
      if (server) {
        savedAt.value = toDate(server.updated_at)
        status.value = 'saved'
      } else if (local) {
        status.value = 'local-only'
      } else {
        status.value = 'idle'
      }
    }

    if (serverError) {
      errorMessage.value = serverError.message
      failureKind.value = 'save'
    }

    lastKey = currentKey
    loading.value = false
  }

  function handlePageHide(): void {
    if (closed || disposed) return

    if (hasMeaningfulDraftContent(options.content())) flushLocalNow()
    else clearLocalNow()
  }

  watch(options.content, handleContentChange, { deep: true })

  watch(
    () => (options.enabled ? options.enabled() : true),
    (enabled, wasEnabled) => {
      if (enabled === wasEnabled) return

      if (!enabled) {
        cancelServerTimer()
        if (dirty) flushLocalNow()
        if (dirty && canSyncServer() && hasMeaningfulDraftContent(options.content())) {
          // Flush the text draft before image-mode subject edits can reach it.
          void performServerSave()
        }
        return
      }

      // Image-mode edits are not text-draft content; adopt them as the new
      // baseline so switching back does not start a surprise save.
      lastKey = draftContentKey(options.content())
    },
  )

  onMounted(() => {
    if (typeof window !== 'undefined') window.addEventListener('pagehide', handlePageHide)
    void load()
  })

  onBeforeUnmount(() => {
    if (typeof window !== 'undefined') window.removeEventListener('pagehide', handlePageHide)
    if (closed) {
      disposed = true
      cancelTimers()
      return
    }

    const enabled = isEnabled()
    const content = options.content()
    const meaningful = hasMeaningfulDraftContent(content)

    if (meaningful) flushLocalNow()
    else clearLocalNow()

    const shouldPush = enabled && meaningful && dirty && canSyncServer()
    if (shouldPush) void performServerSave()
    else if (!meaningful && enabled && dirty && canSyncServer()) void deleteServerDraft()

    disposed = true
    cancelTimers()
  })

  return {
    status,
    savedAt,
    errorMessage,
    conflict,
    candidate,
    candidateVisible,
    hasHiddenCandidate,
    hasDraft,
    blockedReason,
    loading,
    resolvingConflict,
    busy,
    load,
    restore,
    dismissRestore,
    showRestore,
    discard,
    retry,
    resolveConflict,
    prepareSubmit,
    cancelSubmit,
    clearAfterSubmit,
  }
}
