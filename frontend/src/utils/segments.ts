import type { Difficulty, GenerationTargetIndex, Task } from '../api/types'

export const SEGMENT_INDEXES: readonly GenerationTargetIndex[] = [1, 2, 3]

export const SEGMENT_DEFAULT_DIFFICULTIES: Record<GenerationTargetIndex, Difficulty> = {
  1: 'easy',
  2: 'medium',
  3: 'hard',
}

export type SegmentStatus = 'waiting' | Task['status']
export type SegmentGroupStatus =
  'waiting' | 'queued' | 'running' | 'done' | 'partial-failed' | 'failed'

export interface SegmentGroupSummary {
  doneCount: number
  failedCount: number
  activeCount: number
  status: SegmentGroupStatus
}

export interface QuizSegmentGroup extends SegmentGroupSummary {
  questionId: number
  tasks: Task[]
  latestCreatedAt: string
}

const SEGMENT_STATUS_LABELS: Record<SegmentStatus, string> = {
  waiting: '等待生成',
  queued: '排队中',
  running: '生成中',
  done: '已完成',
  failed: '失败',
}

const GROUP_STATUS_LABELS: Record<SegmentGroupStatus, string> = {
  waiting: '等待中',
  queued: '排队',
  running: '生成中',
  done: '完成',
  'partial-failed': '部分失败',
  failed: '失败',
}

export function isSegmentIndex(value: number | null | undefined): value is GenerationTargetIndex {
  return value === 1 || value === 2 || value === 3
}

export function isSegmentTask(task: Task): boolean {
  return task.stage === 'quiz' && isSegmentIndex(task.target_index)
}

export function segmentDifficulty(task: Task | null, index: GenerationTargetIndex): Difficulty {
  return task?.difficulty ?? SEGMENT_DEFAULT_DIFFICULTIES[index]
}

export function segmentStatusLabel(status: SegmentStatus): string {
  return SEGMENT_STATUS_LABELS[status]
}

export function segmentGroupStatusLabel(status: SegmentGroupStatus): string {
  return GROUP_STATUS_LABELS[status]
}

function isNewerTask(candidate: Task, current: Task): boolean {
  if (candidate.created_at !== current.created_at) {
    return candidate.created_at > current.created_at
  }
  return candidate.id > current.id
}

export function latestSegmentTask(tasks: Task[], index: GenerationTargetIndex): Task | null {
  let latest: Task | null = null

  for (const task of tasks) {
    if (!isSegmentTask(task) || task.target_index !== index) continue
    if (!latest || isNewerTask(task, latest)) latest = task
  }

  return latest
}

export function summarizeSegments(tasks: Task[]): SegmentGroupSummary {
  const slots = SEGMENT_INDEXES.map((index) => latestSegmentTask(tasks, index))
  const present = slots.filter((task): task is Task => task !== null)
  const doneCount = present.filter((task) => task.status === 'done').length
  const failedCount = present.filter((task) => task.status === 'failed').length
  const activeCount = present.filter(
    (task) => task.status === 'queued' || task.status === 'running',
  ).length

  let status: SegmentGroupStatus = 'waiting'
  if (present.length === 0) {
    status = 'waiting'
  } else if (present.some((task) => task.status === 'running')) {
    status = 'running'
  } else if (present.some((task) => task.status === 'queued')) {
    status = 'queued'
  } else if (doneCount === SEGMENT_INDEXES.length) {
    status = 'done'
  } else if (failedCount > 0 && doneCount === 0) {
    status = 'failed'
  } else if (failedCount > 0) {
    status = 'partial-failed'
  }

  return { doneCount, failedCount, activeCount, status }
}

export function groupQuizSegmentTasks(tasks: Task[]): QuizSegmentGroup[] {
  const buckets = new Map<number, Task[]>()

  for (const task of tasks) {
    if (!isSegmentTask(task)) continue

    const bucket = buckets.get(task.question_id)
    if (bucket) bucket.push(task)
    else buckets.set(task.question_id, [task])
  }

  const groups: QuizSegmentGroup[] = []

  for (const [questionId, bucket] of buckets) {
    const slots = SEGMENT_INDEXES.map((index) => latestSegmentTask(bucket, index)).filter(
      (task): task is Task => task !== null,
    )
    const latestCreatedAt = slots.reduce(
      (latest, task) => (task.created_at > latest ? task.created_at : latest),
      '',
    )

    groups.push({
      questionId,
      tasks: slots,
      latestCreatedAt,
      ...summarizeSegments(bucket),
    })
  }

  return groups
}
