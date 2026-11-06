import { describe, expect, it } from 'vitest'
import type { Task } from '../src/api/types'
import {
  hasActiveTasks,
  latestTask,
  taskErrorMessage,
  taskFailureMessage,
} from '../src/utils/task'

function makeTask(overrides: Partial<Task>): Task {
  return {
    id: 1,
    question_id: 10,
    stage: 'quiz',
    status: 'queued',
    target_index: null,
    retry_index: 0,
    error_code: null,
    created_at: '2026-11-07T00:00:00Z',
    started_at: null,
    finished_at: null,
    ...overrides,
  }
}

describe('task helpers', () => {
  it('maps canonical backend error codes', () => {
    expect(taskErrorMessage('AI_INVALID_OUTPUT')).toContain('AI 返回结果不完整')
    expect(taskErrorMessage('AI_PROVIDER_ERROR')).toContain('AI 服务暂时不可用')
    expect(taskErrorMessage('AI_INVALID_KEY')).toContain('API Key')
    expect(taskErrorMessage('UNKNOWN_CODE')).toBe('任务失败（UNKNOWN_CODE），请重试。')
  })

  it('prefers the human-readable error message', () => {
    expect(
      taskFailureMessage({
        error_code: 'AI_TIMEOUT',
        error_message: '服务端超时，请稍后重试',
      }),
    ).toBe('服务端超时，请稍后重试')
  })

  it('detects active tasks and the latest stage task', () => {
    const tasks = [
      makeTask({ id: 2, status: 'running' }),
      makeTask({ id: 5, status: 'done' }),
      makeTask({ id: 9, status: 'failed', stage: 'analysis' }),
    ]

    expect(hasActiveTasks(tasks)).toBe(true)
    expect(latestTask(tasks, 'quiz')?.id).toBe(5)
    expect(latestTask(tasks, 'analysis')?.id).toBe(9)
  })
})
