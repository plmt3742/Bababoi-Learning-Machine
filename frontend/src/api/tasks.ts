import apiClient from './client'
import type { Task, TaskListQuery, TaskListResponse } from './types'

export async function listTasks(params: TaskListQuery = {}): Promise<TaskListResponse> {
  const { data } = await apiClient.get<TaskListResponse>('/tasks', { params })
  return data
}

export async function retryTask(id: number): Promise<Task> {
  const { data } = await apiClient.post<Task>(`/tasks/${id}/retry`)
  return data
}
