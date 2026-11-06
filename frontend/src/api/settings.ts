import apiClient from './client'
import type {
  AiSettings,
  AiSettingsUpdate,
  PreferenceSettings,
  PreferenceSettingsUpdate,
} from './types'

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

export async function getPreferences(): Promise<PreferenceSettings> {
  const { data } = await apiClient.get<PreferenceSettings>('/settings/preferences')
  return data
}

export async function savePreferences(
  payload: PreferenceSettingsUpdate,
): Promise<PreferenceSettings> {
  const { data } = await apiClient.put<PreferenceSettings>('/settings/preferences', payload)
  return data
}
