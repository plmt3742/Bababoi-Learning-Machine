import type { Task, TaskStage, TaskStatus } from '../api/types'

const TASK_STAGE_LABELS: Record<TaskStage, string> = {
  analysis: '分析',
  quiz: '生成题',
}

const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  queued: '排队中',
  running: '进行中',
  done: '完成',
  failed: '失败',
}

const TASK_STATUS_COLORS: Record<TaskStatus, string> = {
  queued: 'gray',
  running: 'arcoblue',
  done: 'green',
  failed: 'red',
}

const TASK_ERROR_MESSAGES: Record<string, string> = {
  AI_TIMEOUT: 'AI 服务响应超时，请重试。',
  AI_PROVIDER_ERROR: 'AI 服务暂时不可用，请稍后重试。',
  AI_RATE_LIMITED: 'AI 调用次数过多，请稍后重试。',
  AI_INVALID_OUTPUT: 'AI 返回结果不完整，请重试。',
  AI_INVALID_IMAGE: '图片无法识别，请裁剪后重试。',
  AI_INVALID_KEY: '个人 API Key 无效，请到设置页检查。',
  TASK_NOT_FOUND: '任务不存在或已被清理。',
  VALIDATION_ERROR: '提交内容未通过校验，请检查后重试。',
  INTERNAL_ERROR: '服务端处理失败，请稍后重试。',
}

export function isActiveTaskStatus(status: TaskStatus): boolean {
  return status === 'queued' || status === 'running'
}

export function isActiveTask(task: Task): boolean {
  return isActiveTaskStatus(task.status)
}

export function hasActiveTasks(tasks: Task[]): boolean {
  return tasks.some(isActiveTask)
}

export function taskStageLabel(stage: TaskStage | null | undefined): string {
  return stage ? TASK_STAGE_LABELS[stage] : '任务'
}

export function taskStatusLabel(status: TaskStatus): string {
  return TASK_STATUS_LABELS[status]
}

export function taskStatusColor(status: TaskStatus): string {
  return TASK_STATUS_COLORS[status]
}

export function taskErrorMessage(code: string | null): string {
  if (!code) return '任务没有成功完成，请重试。'
  return TASK_ERROR_MESSAGES[code] ?? `任务失败（${code}），请重试。`
}

export function taskFailureMessage(task: Pick<Task, 'error_code' | 'error_message'>): string {
  return task.error_message?.trim() || taskErrorMessage(task.error_code)
}

/** Latest task for a stage, ordered by id so it also works with unsorted task lists. */
export function latestTask(tasks: Task[], stage: TaskStage): Task | null {
  let latest: Task | null = null

  for (const task of tasks) {
    if (task.stage !== stage) continue
    if (!latest || task.id > latest.id) latest = task
  }

  return latest
}
