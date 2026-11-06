import apiClient from './client'
import type { AiSettings, AiSettingsUpdate } from './types'

export async function getAiSettings(): Promise<AiSettings> {
  const { data } = await apiClient.get<AiSettings>('/settings/ai')
  return data
}

export async function saveAiSettings(payload: AiSettingsUpdate): Promise<AiSettings> {
  const { data } = await apiClient.put<AiSettings>('/settings/ai', payload)
  return data
}

export async function deleteAiSettings(): Promise<void> {
  await apiClient.delete('/settings/ai')
}
