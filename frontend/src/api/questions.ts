import apiClient from './client'
import type {
  Difficulty,
  GenerateQuestionsPayload,
  GenerateTaskRef,
  GenerateTasksResponse,
  GenerationTargetIndex,
  PaginatedResponse,
  Question,
  QuestionCreate,
  QuestionCreateResult,
  QuestionDetail,
  QuestionListItem,
  QuestionListQuery,
  QuestionUpdate,
  TaskIdResponse,
} from './types'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function toTargetIndex(value: unknown): GenerationTargetIndex | null {
  return value === 1 || value === 2 || value === 3 ? value : null
}

function toDifficulty(value: unknown): Difficulty | null {
  return value === 'easy' || value === 'medium' || value === 'hard' ? value : null
}

function toGenerateTaskRef(value: unknown): GenerateTaskRef | null {
  if (!isRecord(value) || typeof value.task_id !== 'number') return null

  return {
    task_id: value.task_id,
    target_index: toTargetIndex(value.target_index),
    difficulty: toDifficulty(value.difficulty),
  }
}

export function normalizeGenerateResponse(data: unknown): GenerateTasksResponse {
  if (!isRecord(data)) throw new Error('生成接口返回格式不正确')

  const rawTasks: unknown = data.tasks
  if (Array.isArray(rawTasks)) {
    const tasks: GenerateTaskRef[] = []
    for (const item of rawTasks) {
      const task = toGenerateTaskRef(item)
      if (task) tasks.push(task)
    }
    if (tasks.length > 0) return { tasks }
  }

  throw new Error('生成接口返回格式不正确')
}

export async function listQuestions(
  params: QuestionListQuery = {},
): Promise<PaginatedResponse<QuestionListItem>> {
  const { data } = await apiClient.get<PaginatedResponse<QuestionListItem>>('/questions', {
    params,
  })
  return data
}

export async function getQuestion(
  id: number,
  options: { includeGenerated?: boolean } = {},
): Promise<QuestionDetail> {
  const { data } = await apiClient.get<QuestionDetail>(`/questions/${id}`, {
    params: options.includeGenerated ? { include: 'generated' } : undefined,
  })
  return data
}

export async function createQuestion(payload: QuestionCreate): Promise<QuestionCreateResult> {
  const { data } = await apiClient.post<QuestionCreateResult>('/questions', payload)
  return data
}

export async function updateQuestion(id: number, payload: QuestionUpdate): Promise<Question> {
  const { data } = await apiClient.patch<Question>(`/questions/${id}`, payload)
  return data
}

export async function removeQuestion(id: number): Promise<void> {
  await apiClient.delete(`/questions/${id}`)
}

export async function analyzeQuestion(id: number): Promise<TaskIdResponse> {
  const { data } = await apiClient.post<TaskIdResponse>(`/questions/${id}/analyze`)
  return data
}

export async function generateQuestions(
  id: number,
  payload?: GenerateQuestionsPayload,
): Promise<GenerateTasksResponse> {
  const { data } = await apiClient.post<unknown>(`/questions/${id}/generate`, payload)
  return normalizeGenerateResponse(data)
}
