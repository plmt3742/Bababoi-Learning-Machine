import apiClient from './client'
import type { Draft, DraftSavePayload } from './types'

/** 200 with a draft, or 204 when the account has none yet. */
export async function getDraft(): Promise<Draft | null> {
  const response = await apiClient.get<Draft | null>('/drafts/me')

  if (response.status === 204 || !response.data) return null
  return response.data
}

export async function saveDraft(payload: DraftSavePayload): Promise<Draft> {
  const { data } = await apiClient.put<Draft>('/drafts/me', payload)
  return data
}

export async function removeDraft(): Promise<void> {
  await apiClient.delete('/drafts/me')
}
