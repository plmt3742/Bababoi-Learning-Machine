import apiClient from './client'
import type { StatsOverview } from './types'

export async function getStatsOverview(): Promise<StatsOverview> {
  const { data } = await apiClient.get<StatsOverview>('/stats/overview')
  return data
}
