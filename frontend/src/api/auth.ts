import { apiClient } from './client'
import type { User } from './types'

export interface RegisterInput {
  email: string
  password: string
  full_name: string
}

export interface LoginInput {
  email: string
  password: string
}

export const authApi = {
  register: (data: RegisterInput) => apiClient.post<User>('/auth/register', data),
  login: (data: LoginInput) => apiClient.post<User>('/auth/login', data),
  logout: () => apiClient.post<{ message: string }>('/auth/logout'),
  me: () => apiClient.get<User>('/auth/me'),
}
