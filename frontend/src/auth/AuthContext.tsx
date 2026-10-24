import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { authApi, type LoginInput, type RegisterInput } from '../api/auth'
import { ApiError } from '../api/client'
import type { User } from '../api/types'

interface AuthContextValue {
  user: User | null
  status: 'loading' | 'authenticated' | 'unauthenticated'
  login: (data: LoginInput) => Promise<void>
  register: (data: RegisterInput) => Promise<void>
  logout: () => Promise<void>
}

// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<'loading' | 'authenticated' | 'unauthenticated'>('loading')
  const queryClient = useQueryClient()

  // Cached children and insights belong to whoever was signed in. Drop them whenever
  // the account changes so the next parent never sees them, even briefly.
  const clearCachedData = useCallback(() => {
    void queryClient.cancelQueries()
    queryClient.clear()
  }, [queryClient])

  // Bumped by every successful login or register, and by every logout. The startup /me check only applies its
  // result if no such transition happened while it was in flight; otherwise a slow
  // /me could undo a fresh login or resurrect a session the parent just ended.
  const transitionCount = useRef(0)

  const refreshSession = useCallback(async () => {
    const startedAt = transitionCount.current
    try {
      const me = await authApi.me()
      if (transitionCount.current !== startedAt) return
      setUser(me)
      setStatus('authenticated')
    } catch (err) {
      if (transitionCount.current !== startedAt) return
      setUser(null)
      setStatus('unauthenticated')
      if (!(err instanceof ApiError) || err.status !== 401) {
        console.error('Failed to load session', err)
      }
    }
  }, [])

  useEffect(() => {
    void refreshSession()
  }, [refreshSession])

  const login = useCallback(
    async (data: LoginInput) => {
      const loggedInUser = await authApi.login(data)
      transitionCount.current += 1
      clearCachedData()
      setUser(loggedInUser)
      setStatus('authenticated')
    },
    [clearCachedData],
  )

  const register = useCallback(
    async (data: RegisterInput) => {
      const registeredUser = await authApi.register(data)
      transitionCount.current += 1
      clearCachedData()
      setUser(registeredUser)
      setStatus('authenticated')
    },
    [clearCachedData],
  )

  const logout = useCallback(async () => {
    transitionCount.current += 1
    try {
      await authApi.logout()
    } finally {
      clearCachedData()
      setUser(null)
      setStatus('unauthenticated')
    }
  }, [clearCachedData])

  return (
    <AuthContext.Provider value={{ user, status, login, register, logout }}>{children}</AuthContext.Provider>
  )
}
