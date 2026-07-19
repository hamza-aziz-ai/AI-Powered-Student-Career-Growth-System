import { apiClient } from './client'
import type { Child } from './types'

export type ChildCreateInput = {
  first_name: string
  birth_year: number
  grade_level?: string | null
  interests: string[]
  strengths: string[]
  favorite_subjects?: string[] | null
  notes?: string | null
}

export type ChildUpdateInput = Partial<ChildCreateInput>

export const childrenApi = {
  list: () => apiClient.get<Child[]>('/children'),
  get: (childId: string) => apiClient.get<Child>(`/children/${childId}`),
  create: (data: ChildCreateInput) => apiClient.post<Child>('/children', data),
  update: (childId: string, data: ChildUpdateInput) => apiClient.patch<Child>(`/children/${childId}`, data),
  remove: (childId: string) => apiClient.delete<void>(`/children/${childId}`),
}
