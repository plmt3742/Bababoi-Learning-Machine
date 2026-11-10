import { describe, expect, it } from 'vitest'
import type { Task } from '../src/api/types'
import { groupQuizSegmentTasks, summarizeSegments } from '../src/utils/segments'

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 1,
    question_id: 10,
    stage: 'quiz',
    status: 'queued',
    target_index: 1,
    retry_index: 0,
    error_code: null,
    created_at: '2026-11-07T00:00:00Z',
    started_at: null,
    finished_at: null,
    ...overrides,
  }
}

describe('summarizeSegments', () => {
  it('waits with no present tasks', () => {
    expect(summarizeSegments([])).toEqual({
      doneCount: 0,
      failedCount: 0,
      activeCount: 0,
      presentCount: 0,
      status: 'waiting',
    })
  })

  it('completes when all three slots are done', () => {
    const summary = summarizeSegments([
      makeTask({ id: 1, target_index: 1, status: 'done' }),
      makeTask({ id: 2, target_index: 2, status: 'done' }),
      makeTask({ id: 3, target_index: 3, status: 'done' }),
    ])

    expect(summary.status).toBe('done')
    expect(summary.doneCount).toBe(3)
    expect(summary.presentCount).toBe(3)
  })

  it('completes a single requested segment', () => {
    const summary = summarizeSegments([makeTask({ id: 9, target_index: 2, status: 'done' })])

    expect(summary.status).toBe('done')
    expect(summary.doneCount).toBe(1)
    expect(summary.presentCount).toBe(1)
  })

  it('reports partial failure when one of two present segments fails', () => {
    const summary = summarizeSegments([
      makeTask({ id: 1, target_index: 1, status: 'done' }),
      makeTask({ id: 2, target_index: 2, status: 'failed' }),
    ])

    expect(summary.status).toBe('partial-failed')
    expect(summary.presentCount).toBe(2)
    expect(summary.doneCount).toBe(1)
    expect(summary.failedCount).toBe(1)
  })

  it('reports running while any present segment is running', () => {
    const summary = summarizeSegments([
      makeTask({ id: 1, target_index: 1, status: 'running' }),
      makeTask({ id: 2, target_index: 2, status: 'queued' }),
    ])

    expect(summary.status).toBe('running')
  })

  it('fails when every present segment failed', () => {
    const summary = summarizeSegments([
      makeTask({ id: 1, target_index: 1, status: 'failed' }),
      makeTask({ id: 2, target_index: 2, status: 'failed' }),
      makeTask({ id: 3, target_index: 3, status: 'failed' }),
    ])

    expect(summary.status).toBe('failed')
    expect(summary.failedCount).toBe(3)
    expect(summary.presentCount).toBe(3)
  })
})

describe('groupQuizSegmentTasks', () => {
  it('groups by question and keeps the latest task per slot', () => {
    const groups = groupQuizSegmentTasks([
      makeTask({
        id: 1,
        question_id: 10,
        target_index: 1,
        status: 'failed',
        created_at: '2026-11-07T00:00:00Z',
      }),
      makeTask({
        id: 2,
        question_id: 10,
        target_index: 1,
        status: 'done',
        created_at: '2026-11-07T01:00:00Z',
      }),
      makeTask({
        id: 3,
        question_id: 10,
        target_index: 2,
        status: 'done',
        created_at: '2026-11-07T00:30:00Z',
      }),
      makeTask({
        id: 4,
        question_id: 20,
        target_index: 3,
        status: 'done',
        created_at: '2026-11-07T02:00:00Z',
      }),
    ])

    expect(groups).toHaveLength(2)

    const group10 = groups.find((group) => group.questionId === 10)
    expect(group10?.tasks.map((task) => task.id)).toEqual([2, 3])
    expect(group10?.presentCount).toBe(2)
    expect(group10?.doneCount).toBe(2)
    expect(group10?.status).toBe('done')
    expect(group10?.latestCreatedAt).toBe('2026-11-07T01:00:00Z')

    const group20 = groups.find((group) => group.questionId === 20)
    expect(group20?.presentCount).toBe(1)
    expect(group20?.status).toBe('done')
  })
})
