import apiClient from './client'
import type {
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

export async function generateQuestions(id: number): Promise<TaskIdResponse> {
  const { data } = await apiClient.post<TaskIdResponse>(`/questions/${id}/generate`)
  return data
}
