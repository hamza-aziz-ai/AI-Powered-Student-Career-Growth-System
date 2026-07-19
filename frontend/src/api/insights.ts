import { apiClient } from './client'
import type { CareerInsight } from './types'

export const insightsApi = {
  list: (childId: string) => apiClient.get<CareerInsight[]>(`/children/${childId}/insights`),
  get: (childId: string, insightId: string) =>
    apiClient.get<CareerInsight>(`/children/${childId}/insights/${insightId}`),
  generate: (childId: string) => apiClient.post<CareerInsight>(`/children/${childId}/insights`),
}
