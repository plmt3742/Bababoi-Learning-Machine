import apiClient from './client'
import type {
  PaginatedResponse,
  PracticeRecord,
  PracticeRecordCreate,
  PracticeRecordListQuery,
} from './types'

export async function createPracticeRecord(payload: PracticeRecordCreate): Promise<PracticeRecord> {
  const { data } = await apiClient.post<PracticeRecord>('/practice-records', payload)
  return data
}

export async function listPracticeRecords(
  params: PracticeRecordListQuery = {},
): Promise<PaginatedResponse<PracticeRecord>> {
  const { data } = await apiClient.get<PaginatedResponse<PracticeRecord>>('/practice-records', {
    params,
  })
  return data
}
