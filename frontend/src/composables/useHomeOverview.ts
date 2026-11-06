import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getDraft } from '../api/drafts'
import { normalizeApiError } from '../api/errors'
import { listPracticeRecords } from '../api/practice'
import { listQuestions } from '../api/questions'
import { getStatsOverview } from '../api/stats'
import { listTasks } from '../api/tasks'
import type { Draft, QuestionListItem, StatsOverview, Task, TaskStatus } from '../api/types'
import { formatStatsTime } from '../utils/stats'

export const HOME_QUESTION_LIMIT = 5
export const HOME_TASK_LIMIT = 3

export type HomeSection = 'stats' | 'questions' | 'tasks' | 'draft' | 'practice'

export interface HomeSectionError {
  message: string
  code: string
}

export type HomeSectionErrors = Record<HomeSection, HomeSectionError | null>

const TASK_PRIORITY: Record<TaskStatus, number> = {
  failed: 0,
  running: 1,
  queued: 2,
  done: 3,
}

function emptyErrors(): HomeSectionErrors {
  return {
    stats: null,
    questions: null,
    tasks: null,
    draft: null,
    practice: null,
  }
}

function toSectionError(cause: unknown): HomeSectionError {
  const error = normalizeApiError(cause)
  return { message: error.message, code: error.code }
}

/**
 * One overview request per section so a missing P1 stats endpoint (BE-013)
 * cannot blank the rest of the home dashboard. Failed sections keep previously
 * loaded data and expose an inline error for the page to render.
 */
export function useHomeOverview() {
  const stats = ref<StatsOverview | null>(null)
  const questions = ref<QuestionListItem[]>([])
  const questionTotal = ref<number | null>(null)
  const tasks = ref<Task[]>([])
  const draft = ref<Draft | null>(null)
  const practiceTotal = ref<number | null>(null)

  const errors = ref<HomeSectionErrors>(emptyErrors())
  const loading = ref(true)
  const refreshing = ref(false)

  let requestToken = 0

  const activeTasks = computed(() =>
    tasks.value.filter((task) => task.status === 'queued' || task.status === 'running'),
  )

  const failedTasks = computed(() => tasks.value.filter((task) => task.status === 'failed'))

  /** Failed tasks first, then active work, newest first inside each group. */
  const attentionTasks = computed(() =>
    [...tasks.value]
      .filter(
        (task) => task.status === 'failed' || task.status === 'queued' || task.status === 'running',
      )
      .sort(
        (left, right) =>
          TASK_PRIORITY[left.status] - TASK_PRIORITY[right.status] ||
          right.created_at.localeCompare(left.created_at) ||
          right.id - left.id,
      )
      .slice(0, HOME_TASK_LIMIT),
  )

  const weakPoints = computed(() => stats.value?.weak_knowledge_points ?? [])

  const lastUpdatedText = computed(() =>
    stats.value ? formatStatsTime(stats.value.updated_at) : '',
  )

  const allFailed = computed(() => {
    const coreSections: HomeSection[] = ['stats', 'questions', 'tasks', 'draft']
    return coreSections.every((section) => errors.value[section] !== null)
  })

  async function load(mode: 'initial' | 'refresh'): Promise<void> {
    const token = ++requestToken
    errors.value = emptyErrors()

    if (mode === 'initial') loading.value = true
    else refreshing.value = true

    try {
      const [statsResult, questionsResult, tasksResult, draftResult, practiceResult] =
        await Promise.allSettled([
          getStatsOverview(),
          listQuestions({ page: 1, page_size: HOME_QUESTION_LIMIT, sort: 'created_at_desc' }),
          listTasks({}),
          getDraft(),
          listPracticeRecords({ page: 1, page_size: 1 }),
        ] as const)

      if (token !== requestToken) return

      const nextErrors = emptyErrors()

      if (statsResult.status === 'fulfilled') {
        stats.value = statsResult.value
      } else {
        nextErrors.stats = toSectionError(statsResult.reason)
      }

      if (questionsResult.status === 'fulfilled') {
        questions.value = questionsResult.value.items
        questionTotal.value = questionsResult.value.total
      } else {
        nextErrors.questions = toSectionError(questionsResult.reason)
      }

      if (tasksResult.status === 'fulfilled') {
        tasks.value = tasksResult.value.items
      } else {
        nextErrors.tasks = toSectionError(tasksResult.reason)
      }

      if (draftResult.status === 'fulfilled') {
        draft.value = draftResult.value
      } else {
        nextErrors.draft = toSectionError(draftResult.reason)
      }

      if (practiceResult.status === 'fulfilled') {
        practiceTotal.value = practiceResult.value.total
      } else {
        nextErrors.practice = toSectionError(practiceResult.reason)
      }

      errors.value = nextErrors
    } finally {
      if (token === requestToken) {
        loading.value = false
        refreshing.value = false
      }
    }
  }

  async function refresh(): Promise<void> {
    if (loading.value || refreshing.value) return
    await load('refresh')
  }

  onMounted(() => {
    void load('initial')
  })

  onBeforeUnmount(() => {
    requestToken += 1
  })

  return {
    stats,
    questions,
    questionTotal,
    tasks,
    draft,
    practiceTotal,
    errors,
    loading,
    refreshing,
    activeTasks,
    failedTasks,
    attentionTasks,
    weakPoints,
    lastUpdatedText,
    allFailed,
    refresh,
  }
}
